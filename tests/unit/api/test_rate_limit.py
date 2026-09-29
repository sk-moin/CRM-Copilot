"""The rate limiter's own logic, tested without a running app.

Route-level enforcement (a real 429 over a real Redis) lives in
tests/integration/test_rate_limit_routes.py. This file covers the identifier,
the 429 contract, the lifecycle helpers, and the fail-open path -- the parts
that do not need HTTP round trips to prove.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.exceptions
from fastapi import HTTPException
from starlette.requests import Request

import app.api.rate_limit as rate_limit
from app.api.rate_limit import (
    AUTH_TIER,
    FastAPILimiter,
    _FailOpenRateLimiter,
    _client_address,
    _identifier,
    _too_many_requests,
    init_rate_limiter,
    reset_rate_limiter,
)
from app.core import config
from app.core.security import create_access_token


def _request(*, headers: list[tuple[bytes, bytes]] | None = None, client=("1.2.3.4", 1234)):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/probe",
        "headers": headers or [],
        "client": client,
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


def _bearer_request(token: str):
    return _request(
        headers=[(b"authorization", f"Bearer {token}".encode())],
    )


@pytest.fixture(autouse=True)
async def _clean_limiter_state():
    """Every test starts and ends with a known, uninitialized limiter."""

    await reset_rate_limiter()
    yield
    await reset_rate_limiter()


# --------------------------------------------------------------------------- #
# Identifier
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_an_authenticated_caller_is_keyed_by_tenant_and_user():
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        org_id="33333333-3333-3333-3333-333333333333",
        email="a@example.com",
        role="OWNER",
    )

    identity = await _identifier(_bearer_request(token))

    assert identity == (
        "tenant:22222222-2222-2222-2222-222222222222:"
        "user:11111111-1111-1111-1111-111111111111"
    )


@pytest.mark.asyncio
async def test_auth_tier_uses_ip_key_even_when_bearer_token_is_valid(monkeypatch):
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        org_id="33333333-3333-3333-3333-333333333333",
        email="a@example.com",
        role="OWNER",
    )
    request = _bearer_request(token)
    redis_client = MagicMock()
    redis_client.evalsha = AsyncMock(return_value=0)
    monkeypatch.setattr(FastAPILimiter, "redis", redis_client)
    monkeypatch.setattr(FastAPILimiter, "lua_sha", "deadbeef")
    monkeypatch.setattr(FastAPILimiter, "prefix", "test-rate-limit")
    monkeypatch.setattr(FastAPILimiter, "http_callback", _too_many_requests)

    assert await _identifier(request) == (
        "tenant:22222222-2222-2222-2222-222222222222:"
        "user:11111111-1111-1111-1111-111111111111"
    )
    await AUTH_TIER(request, MagicMock())

    redis_key = redis_client.evalsha.await_args.args[2]
    assert redis_key == "test-rate-limit:auth:ip:1.2.3.4"


@pytest.mark.asyncio
async def test_an_anonymous_caller_is_keyed_by_address():
    identity = await _identifier(_request(client=("203.0.113.5", 1234)))

    assert identity == "ip:203.0.113.5"


@pytest.mark.asyncio
async def test_a_malformed_token_falls_back_to_the_address_rather_than_raising():
    """The identifier runs on every request, including unauthenticated routes.

    It must never be the reason a request to an anonymous endpoint fails.
    """

    request = _bearer_request("not-a-real-jwt")

    identity = await _identifier(request)

    assert identity == "ip:1.2.3.4"


@pytest.mark.asyncio
async def test_an_expired_token_falls_back_to_the_address():
    import jwt as pyjwt

    from datetime import datetime, timedelta, timezone

    expired = pyjwt.encode(
        {
            "sub": "u1",
            "tenant_id": "t1",
            "iss": config.JWT_ISSUER,
            "aud": config.JWT_AUDIENCE,
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        },
        config.JWT_SECRET,
        algorithm=config.TOKEN_ALGORITHM,
    )

    identity = await _identifier(_bearer_request(expired))

    assert identity == "ip:1.2.3.4"


def test_a_non_bearer_authorization_header_is_ignored():
    from app.api.rate_limit import _bearer_token

    assert _bearer_token(_request(headers=[(b"authorization", b"Basic abc123")])) is None
    assert _bearer_token(_request(headers=[(b"authorization", b"Bearer")])) is None
    assert _bearer_token(_request(headers=[])) is None


# --------------------------------------------------------------------------- #
# Client address and the proxy trust boundary
# --------------------------------------------------------------------------- #


def test_untrusted_forwarded_for_is_ignored_by_default(monkeypatch):
    """`TRUSTED_PROXY_COUNT` defaults to 0: the header is never read."""

    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)

    request = _request(
        headers=[(b"x-forwarded-for", b"9.9.9.9")],
        client=("1.2.3.4", 1234),
    )

    assert _client_address(request) == "1.2.3.4"


def test_forwarded_for_is_trusted_for_exactly_the_configured_hop_count(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)

    # One trusted proxy appends exactly one entry: the last one is real,
    # anything before it may have been supplied by the client itself.
    request = _request(
        headers=[(b"x-forwarded-for", b"attacker-forged, real-client")],
        client=("10.0.0.1", 1234),
    )

    assert _client_address(request) == "real-client"


def test_forwarded_for_trusts_the_nth_entry_from_the_end_for_n_proxies(monkeypatch):
    """Two trusted proxies: entries[-2], not entries[-1].

    With N proxies each appending the peer they actually observed, a chain
    of k client-forged entries plus N proxy-appended entries has the real
    client's address at position `-N` from the end -- here, one forged
    entry ("spoofed") ahead of it, and one proxy-appended entry ("proxy-hop")
    behind it: 1 forged + 2 trusted = 3 entries total.
    """

    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)

    request = _request(
        headers=[(b"x-forwarded-for", b"spoofed, real-client, proxy-hop")],
        client=("10.0.0.1", 1234),
    )

    assert _client_address(request) == "real-client"


def test_zero_trusted_proxies_never_indexes_into_forwarded_for(monkeypatch):
    """Regression: Python's `entries[-0]` is `entries[0]`, not "no entries".

    With TRUSTED_PROXY_COUNT=0 a naive `entries[-trusted]` would read the
    first, fully attacker-controlled entry instead of skipping the header.
    """

    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)

    request = _request(
        headers=[(b"x-forwarded-for", b"attacker-chosen-address")],
        client=("10.0.0.1", 1234),
    )

    assert _client_address(request) == "10.0.0.1"


def test_too_few_forwarded_for_entries_falls_back_to_the_direct_peer(monkeypatch):
    """Fewer entries than trusted hops is an anomaly, not a green light."""

    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 3)

    request = _request(
        headers=[(b"x-forwarded-for", b"only-one-entry")],
        client=("10.0.0.1", 1234),
    )

    assert _client_address(request) == "10.0.0.1"


def test_no_client_at_all_does_not_crash():
    request = _request(client=None)

    assert _client_address(request) == "unknown"


# --------------------------------------------------------------------------- #
# The 429 contract
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_the_429_names_a_wait_time_and_no_internal_detail():
    with pytest.raises(HTTPException) as excinfo:
        await _too_many_requests(_request(), MagicMock(), 37_000)

    exc = excinfo.value

    assert exc.status_code == 429
    assert exc.headers["Retry-After"] == "37"
    assert exc.detail == "Too many requests. Retry in 37 seconds."

    # No bucket key, tier name, or Redis detail leaks into the message.
    for leak in ("crm_copilot", "rate_limit", "redis", "tier"):
        assert leak not in exc.detail.lower()


@pytest.mark.asyncio
async def test_the_retry_after_rounds_up_never_down():
    """A caller told to wait 0 seconds would retry immediately and be limited again."""

    with pytest.raises(HTTPException) as excinfo:
        await _too_many_requests(_request(), MagicMock(), 1)  # 1ms remaining

    assert excinfo.value.headers["Retry-After"] == "1"


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_init_wires_the_limiter_to_the_projects_redis_client():
    await init_rate_limiter()

    assert FastAPILimiter.redis is not None
    assert FastAPILimiter.prefix == config.RATE_LIMIT_PREFIX
    assert FastAPILimiter.identifier is _identifier
    assert FastAPILimiter.http_callback is _too_many_requests


@pytest.mark.asyncio
async def test_reset_drops_the_reference_without_closing_the_shared_client():
    """`reset_redis()` owns closing the client; this must not race it.

    If reset_rate_limiter() closed the connection itself, the shared client
    other parts of the app still hold a reference to -- auth's refresh-token
    storage, the job queue -- would be closed out from under them.
    """

    await init_rate_limiter()

    redis_client = FastAPILimiter.redis

    await reset_rate_limiter()

    assert FastAPILimiter.redis is None

    # Still open: a ping on the client this test still holds a reference to
    # succeeds, proving reset_rate_limiter() did not close it.
    assert await redis_client.ping() is True


@pytest.mark.asyncio
async def test_init_does_not_raise_when_redis_is_unreachable(monkeypatch):
    """A Redis outage at boot must not take the API down with it."""

    class _Unreachable:
        async def script_load(self, *_args, **_kwargs):
            raise redis.exceptions.ConnectionError("refused")

    monkeypatch.setattr(rate_limit, "get_redis", lambda: _Unreachable())

    await init_rate_limiter()  # must not raise

    assert FastAPILimiter.redis is None


# --------------------------------------------------------------------------- #
# Fail open when Redis is unreachable mid-request
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_request_succeeds_when_the_limiter_was_never_initialized():
    tier = _FailOpenRateLimiter(tier="probe", times=1, seconds=60)

    # No exception, and the request is allowed through.
    await tier(_request(), MagicMock())


@pytest.mark.asyncio
async def test_a_redis_error_mid_check_lets_the_request_through_and_warns(
    monkeypatch,
    caplog,
):
    tier = _FailOpenRateLimiter(tier="probe", times=1, seconds=60)

    broken_redis = MagicMock()
    broken_redis.evalsha = AsyncMock(
        side_effect=redis.exceptions.ConnectionError("connection refused")
    )

    monkeypatch.setattr(FastAPILimiter, "redis", broken_redis)
    monkeypatch.setattr(FastAPILimiter, "lua_sha", "deadbeef")
    monkeypatch.setattr(FastAPILimiter, "identifier", _identifier)
    monkeypatch.setattr(rate_limit, "_last_warning_at", 0.0)

    with caplog.at_level("WARNING"):
        await tier(_request(), MagicMock())  # must not raise

    assert any("rate_limit.redis_unavailable" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_the_outage_warning_is_not_repeated_within_the_cooldown(monkeypatch, caplog):
    tier = _FailOpenRateLimiter(tier="probe", times=1, seconds=60)

    broken_redis = MagicMock()
    broken_redis.evalsha = AsyncMock(
        side_effect=redis.exceptions.ConnectionError("connection refused")
    )

    monkeypatch.setattr(FastAPILimiter, "redis", broken_redis)
    monkeypatch.setattr(FastAPILimiter, "lua_sha", "deadbeef")
    monkeypatch.setattr(FastAPILimiter, "identifier", _identifier)
    monkeypatch.setattr(rate_limit, "_last_warning_at", 0.0)
    monkeypatch.setattr(rate_limit, "_WARNING_COOLDOWN_SECONDS", 3600.0)

    with caplog.at_level("WARNING"):
        await tier(_request(), MagicMock())
        await tier(_request(), MagicMock())
        await tier(_request(), MagicMock())

    warnings = [r for r in caplog.records if "rate_limit.redis_unavailable" in r.message]

    assert len(warnings) == 1, "the outage was logged once per request, not once per outage"


@pytest.mark.asyncio
async def test_a_legitimate_429_is_not_swallowed_as_a_redis_error(monkeypatch):
    """The fail-open catch is narrow: only RedisError, never HTTPException."""

    tier = _FailOpenRateLimiter(tier="probe", times=1, seconds=60)

    healthy_redis = MagicMock()
    healthy_redis.evalsha = AsyncMock(return_value=5000)  # exhausted, 5s left

    monkeypatch.setattr(FastAPILimiter, "redis", healthy_redis)
    monkeypatch.setattr(FastAPILimiter, "lua_sha", "deadbeef")
    monkeypatch.setattr(FastAPILimiter, "identifier", _identifier)
    monkeypatch.setattr(FastAPILimiter, "http_callback", _too_many_requests)

    with pytest.raises(HTTPException) as excinfo:
        await tier(_request(), MagicMock())

    assert excinfo.value.status_code == 429


# --------------------------------------------------------------------------- #
# Settings bounds
# --------------------------------------------------------------------------- #


def test_the_tier_settings_refuse_non_positive_values():
    from pydantic import ValidationError

    from app.core.config import Settings

    for field in (
        "RATE_LIMIT_AUTH_TIMES",
        "RATE_LIMIT_AUTH_SECONDS",
        "RATE_LIMIT_AI_TIMES",
        "RATE_LIMIT_AI_SECONDS",
        "RATE_LIMIT_DEFAULT_TIMES",
        "RATE_LIMIT_DEFAULT_SECONDS",
    ):
        with pytest.raises(ValidationError):
            Settings(**{field: 0})


def test_trusted_proxy_count_allows_zero_but_not_negative():
    from pydantic import ValidationError

    from app.core.config import Settings

    assert Settings(TRUSTED_PROXY_COUNT=0).TRUSTED_PROXY_COUNT == 0

    with pytest.raises(ValidationError):
        Settings(TRUSTED_PROXY_COUNT=-1)
