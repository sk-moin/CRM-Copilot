"""Redis-backed per-tenant/per-user request throttling.

Three fixed-window tiers, because cost per request genuinely differs:

* **auth** - strict, IP-keyed. Guards the unauthenticated login/register
  routes against brute-force and enumeration.
* **ai** - strict, tenant/user-keyed. Guards the routes that spend LLM or
  embedding budget: chat, RAG query, and document upload (which enqueues a
  worker job).
* **default** - generous, tenant/user-keyed. Everything else authenticated.

Built on `fastapi-limiter`, pinned to the pre-0.2 release that talks to Redis
directly via a Lua script -- see requirements.txt for why. One shared
`FastAPILimiter.init()` call supplies the identifier and the 429 shape; the
three tiers below only differ in `times`/`seconds`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Final

import redis.exceptions
from fastapi import HTTPException, Request, Response
from fastapi_limiter import FastAPILimiter
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core import config
from app.core.redis_client import get_redis
from app.core.security import JWTError, decode_jwt

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Identifier: who is asking
# --------------------------------------------------------------------------- #


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")

    if not header:
        return None

    scheme, _, token = header.partition(" ")

    if scheme.lower() != "bearer" or not token:
        return None

    return token


def _client_address(request: Request) -> str:
    """The address to bucket an anonymous caller by.

    `X-Forwarded-For` is client-supplied and trivially spoofed, so it is
    trusted only for exactly `TRUSTED_PROXY_COUNT` hops -- the reverse
    proxies this deployment actually puts in front of the app. With N
    trusted proxies each faithfully appending the peer they observed, the
    real client's address is the N-th entry from the end: `entries[-N]` in
    Python's negative indexing. `TRUSTED_PROXY_COUNT=0` (the default) skips
    the header entirely; `entries[-0]` is `entries[0]` in Python, which
    would let an attacker pick their own bucket by supplying any XFF value,
    so that case is a separate branch rather than falling out of the
    arithmetic.
    """

    trusted = config.TRUSTED_PROXY_COUNT

    if trusted > 0:
        forwarded = request.headers.get("x-forwarded-for")

        if forwarded:
            entries = [part.strip() for part in forwarded.split(",") if part.strip()]

            if len(entries) >= trusted:
                return entries[-trusted]

    if request.client is None:
        return "unknown"

    return request.client.host


async def _identifier(request: Request) -> str:
    """`tenant:<id>:user:<id>` for an authenticated caller, `ip:<addr>` otherwise.

    Reads the same signed JWT `get_current_user` trusts, decoded directly
    rather than through that dependency: the identifier signature
    `fastapi-limiter` calls only receives the request, and a rate-limit check
    runs on every single request, so a second database round trip per
    request to re-resolve the user is not free. The trust boundary is the
    same either way -- a validated JWT signature -- so this reuses that
    boundary rather than the dependency function itself.

    A missing, malformed or expired token falls back to the IP bucket rather
    than raising: this identifier must never be the reason an anonymous
    request fails, since some tiered routes are intentionally unauthenticated.
    """

    token = _bearer_token(request)

    if token is not None:
        try:
            payload = decode_jwt(token)
        except JWTError:
            payload = None

        if payload is not None:
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")

            if user_id and tenant_id:
                return f"tenant:{tenant_id}:user:{user_id}"

    return f"ip:{_client_address(request)}"


async def _auth_identifier(request: Request) -> str:
    """Auth routes always share a bucket per client address, even with a JWT."""

    return f"ip:{_client_address(request)}"


# --------------------------------------------------------------------------- #
# The 429 contract
# --------------------------------------------------------------------------- #


async def _too_many_requests(
    request: Request,
    response: Response,
    pexpire: int,
) -> None:
    """Raised by fastapi-limiter when a bucket is exhausted.

    `pexpire` is milliseconds remaining on the window, straight from Redis's
    PTTL. The message names no internal detail -- no bucket key, no tier
    name, no Redis error -- following the same rule feature 011 applied to
    `error_message`.
    """

    retry_after = max(1, -(-pexpire // 1000))  # ceil division, no float

    raise HTTPException(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many requests. Retry in {retry_after} seconds.",
        headers={"Retry-After": str(retry_after)},
    )


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


async def init_rate_limiter() -> None:
    """Wire the limiter to this app's Redis client.

    Best effort: `FastAPILimiter.init` loads a Lua script, which means it
    talks to Redis synchronously at startup. A Redis outage at boot must not
    take the API down with it -- Redis is already treated as rebuildable
    state everywhere else in this project -- so a failure here is logged and
    left for the tiers themselves to fail open on, the same as a Redis
    outage discovered mid-request.
    """

    try:
        await FastAPILimiter.init(
            get_redis(),
            prefix=config.RATE_LIMIT_PREFIX,
            identifier=_identifier,
            http_callback=_too_many_requests,
        )
    except redis.exceptions.RedisError:
        # FastAPILimiter.init() sets cls.redis *before* awaiting
        # script_load(), so a failure here leaves cls.redis pointing at an
        # unreachable client with no lua_sha -- a worse state than never
        # having initialized at all, because _FailOpenRateLimiter's guard
        # checks exactly `FastAPILimiter.redis is None` and would no longer
        # see it. Reset fully rather than leaving the half-set state behind.
        await reset_rate_limiter()

        logger.warning(
            "rate_limit.init_failed",
            exc_info=True,
            extra={
                "detail": (
                    "Redis unreachable at startup; requests are unthrottled "
                    "until it recovers."
                )
            },
        )


async def reset_rate_limiter() -> None:
    """Drop the limiter's reference to the client without closing it.

    `reset_redis()` owns closing the shared client. This only clears
    `FastAPILimiter`'s class-level state, which is what needs resetting
    between event loops -- pytest-asyncio gives each test a new one, and the
    limiter's `redis` attribute would otherwise point at a pool bound to a
    closed loop.
    """

    FastAPILimiter.redis = None
    FastAPILimiter.lua_sha = None


# --------------------------------------------------------------------------- #
# Fail open when Redis is unreachable
# --------------------------------------------------------------------------- #


_WARNING_COOLDOWN_SECONDS: Final[float] = 60.0
_last_warning_at: float = 0.0


def _warn_once_per_outage(exc: Exception) -> None:
    global _last_warning_at

    now = time.monotonic()

    if now - _last_warning_at >= _WARNING_COOLDOWN_SECONDS:
        _last_warning_at = now
        logger.warning(
            "rate_limit.redis_unavailable",
            exc_info=exc,
            extra={"detail": "Requests are unthrottled until Redis recovers."},
        )


class _FailOpenRateLimiter:
    """One tier: a single shared budget per identifier, not per route.

    `fastapi_limiter.depends.RateLimiter` keys its counter by
    `(identifier, route_index, dep_index)`, which gives every route its own
    independent budget -- so a caller could multiply their real throughput by
    the number of routes in a tier. That is not what "per-tenant/per-user
    throttling" means here: a user's AI-tier budget is one number covering
    chat, RAG query and upload together, not one number each. So this talks
    to `FastAPILimiter`'s Redis client and Lua script directly, with a key
    built from the tier's own name instead of route position.

    Enforced when Redis answers, invisible when it does not: a Redis error
    raised while checking the bucket -- a dropped connection, a timeout --
    lets the request through instead of turning a counter-store outage into
    a 500 for every route in the app. A `429` from a healthy check is an
    `HTTPException`, not a `RedisError`, so it is never caught here.
    """

    def __init__(
        self,
        *,
        tier: str,
        times: int,
        seconds: int,
        identifier: Callable[[Request], Awaitable[str]] | None = None,
    ) -> None:
        self._tier = tier
        self._times = times
        self._milliseconds = seconds * 1000
        self._identifier = identifier

    async def _acquire(self, key: str) -> int:
        redis_client = FastAPILimiter.redis

        try:
            return await redis_client.evalsha(
                FastAPILimiter.lua_sha,
                1,
                key,
                str(self._times),
                str(self._milliseconds),
            )
        except redis.exceptions.NoScriptError:
            FastAPILimiter.lua_sha = await redis_client.script_load(
                FastAPILimiter.lua_script
            )
            return await self._acquire(key)

    async def __call__(self, request: Request, response: Response) -> None:
        if FastAPILimiter.redis is None:
            # Never initialized, or reset between tests/loops. Not an
            # in-request Redis error, but the same outcome applies: nothing
            # to check against, so let the request through.
            return

        try:
            identifier = self._identifier or FastAPILimiter.identifier
            rate_key = await identifier(request)
            key = f"{FastAPILimiter.prefix}:{self._tier}:{rate_key}"
            pexpire = await self._acquire(key)
        except redis.exceptions.RedisError as exc:
            _warn_once_per_outage(exc)
            return

        if pexpire:
            await FastAPILimiter.http_callback(request, response, pexpire)


# --------------------------------------------------------------------------- #
# Tiers
#
# Module-level singletons, not factories: fastapi-limiter's own idiom is
# `Depends(RateLimiter(...))` -- an instance, not a callable that builds one
# per request -- and a singleton is also what lets a test override a tier
# with `app.dependency_overrides[AUTH_TIER] = ...`, keyed by object identity.
# --------------------------------------------------------------------------- #


AUTH_TIER = _FailOpenRateLimiter(
    tier="auth",
    times=config.RATE_LIMIT_AUTH_TIMES,
    seconds=config.RATE_LIMIT_AUTH_SECONDS,
    identifier=_auth_identifier,
)

AI_TIER = _FailOpenRateLimiter(
    tier="ai",
    times=config.RATE_LIMIT_AI_TIMES,
    seconds=config.RATE_LIMIT_AI_SECONDS,
)

DEFAULT_TIER = _FailOpenRateLimiter(
    tier="default",
    times=config.RATE_LIMIT_DEFAULT_TIMES,
    seconds=config.RATE_LIMIT_DEFAULT_SECONDS,
)
