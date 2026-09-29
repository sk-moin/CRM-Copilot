"""Rate limiting enforced through real HTTP requests against a real Redis.

Two kinds of coverage:

* A small throwaway probe app wired to the real tier singletons, so a test
  can drive a route to `429` in a handful of requests without waiting on
  production's much larger default limits, while still exercising the exact
  same dependency and Redis path production uses.
* One test against the real `app.main.app`, proving the actual wiring in
  main.py -- which router got which tier -- and not just the mechanism.

Unit-level coverage (the identifier, the 429 shape, the fail-open path) lives
in tests/unit/api/test_rate_limit.py.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.rate_limit import (
    AI_TIER,
    AUTH_TIER,
    DEFAULT_TIER,
    FastAPILimiter,
    _FailOpenRateLimiter,
    init_rate_limiter,
    reset_rate_limiter,
)

# --------------------------------------------------------------------------- #
# A throwaway app wired to the real tier singletons
# --------------------------------------------------------------------------- #


def _probe_app() -> FastAPI:
    app = FastAPI()

    @app.get("/probe/auth", dependencies=[Depends(AUTH_TIER)])
    async def probe_auth():
        return {"ok": True}

    @app.get("/probe/ai", dependencies=[Depends(AI_TIER)])
    async def probe_ai():
        return {"ok": True}

    @app.get("/probe/default-a", dependencies=[Depends(DEFAULT_TIER)])
    async def probe_default_a():
        return {"ok": True}

    @app.get("/probe/default-b", dependencies=[Depends(DEFAULT_TIER)])
    async def probe_default_b():
        return {"ok": True}

    return app


@pytest_asyncio.fixture
async def probe_app():
    """A tiny app wired to the real tiers, with small per-test budgets."""

    app = _probe_app()

    await init_rate_limiter()

    app.dependency_overrides[AUTH_TIER] = _FailOpenRateLimiter(
        tier="test-auth", times=2, seconds=60
    )
    app.dependency_overrides[AI_TIER] = _FailOpenRateLimiter(
        tier="test-ai", times=2, seconds=60
    )
    app.dependency_overrides[DEFAULT_TIER] = _FailOpenRateLimiter(
        tier="test-default", times=3, seconds=60
    )

    yield app

    # Clean up whatever keys this test's identifier touched, so a later test
    # in the same run never inherits a stale count.
    redis_client = FastAPILimiter.redis
    if redis_client is not None:
        prefix = FastAPILimiter.prefix
        async for key in redis_client.scan_iter(match=f"{prefix}:test-*"):
            await redis_client.delete(key)

    await reset_rate_limiter()


@pytest_asyncio.fixture
async def probe_client(probe_app):
    async with AsyncClient(
        transport=ASGITransport(app=probe_app, client=("198.51.100.7", 1234)),
        base_url="http://test",
    ) as client:
        yield client


# --------------------------------------------------------------------------- #
# The 429 contract, over real HTTP
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_exhausting_a_tier_returns_429_with_retry_after(probe_client):
    for _ in range(2):
        response = await probe_client.get("/probe/auth")
        assert response.status_code == 200

    response = await probe_client.get("/probe/auth")

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0

    body = response.json()
    assert body["detail"].startswith("Too many requests.")


# --------------------------------------------------------------------------- #
# Tiers are independent of each other
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_exhausting_the_ai_tier_does_not_affect_the_default_tier(probe_client):
    for _ in range(2):
        assert (await probe_client.get("/probe/ai")).status_code == 200

    assert (await probe_client.get("/probe/ai")).status_code == 429

    # A different tier, same caller: untouched.
    assert (await probe_client.get("/probe/default-a")).status_code == 200


# --------------------------------------------------------------------------- #
# One shared bucket per tier, not one per route
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_the_same_caller_shares_one_bucket_across_routes_in_a_tier(
    probe_client,
):
    """The point of building a custom key instead of using the library's.

    fastapi-limiter's own default key includes the route, which would give
    every route its own independent budget -- a caller could multiply their
    real throughput by the number of routes in a tier. Here the budget is 3
    total, split across two different routes.
    """

    assert (await probe_client.get("/probe/default-a")).status_code == 200
    assert (await probe_client.get("/probe/default-b")).status_code == 200
    assert (await probe_client.get("/probe/default-a")).status_code == 200

    # The fourth request, on either route, is the one that should be over
    # budget -- the count is combined, not 3 per route.
    response = await probe_client.get("/probe/default-b")

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_different_callers_do_not_share_a_bucket(probe_app, probe_client):
    """The other half of "shared bucket": shared per identity, not globally."""

    for _ in range(2):
        assert (await probe_client.get("/probe/auth")).status_code == 200

    assert (await probe_client.get("/probe/auth")).status_code == 429

    # A second client, a different address, is a different bucket entirely.
    async with AsyncClient(
        transport=ASGITransport(app=probe_app, client=("198.51.100.99", 1234)),
        base_url="http://test",
    ) as other:
        assert (await other.get("/probe/auth")).status_code == 200


# --------------------------------------------------------------------------- #
# The real app: proving the wiring, not just the mechanism
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def real_app_limiter():
    """Init on the real app, guaranteed reset even if setup itself fails.

    Deliberately not a bare try/finally inside each test: a fixture's
    teardown still runs when the test body raises, but an exception raised
    *before* an inline try block -- during init, or while setting an
    override -- would skip an inline finally entirely and leave rate
    limiting stuck initialized against `app.main.app` for the rest of the
    test session.
    """

    from app.main import app as real_app

    await init_rate_limiter()

    yield real_app

    real_app.dependency_overrides.pop(AUTH_TIER, None)
    real_app.dependency_overrides.pop(DEFAULT_TIER, None)

    redis_client = FastAPILimiter.redis
    if redis_client is not None:
        prefix = FastAPILimiter.prefix
        async for key in redis_client.scan_iter(match=f"{prefix}:test-*"):
            await redis_client.delete(key)
        async for key in redis_client.scan_iter(match=f"{prefix}:default:*"):
            await redis_client.delete(key)

    await reset_rate_limiter()


@pytest.mark.asyncio
async def test_the_login_route_is_rate_limited_in_the_real_app(
    client,
    real_app_limiter,
):
    """`/api/v1/auth/login` carries AUTH_TIER in app.main, not a copy of it."""

    real_app_limiter.dependency_overrides[AUTH_TIER] = _FailOpenRateLimiter(
        tier="test-real-auth", times=2, seconds=60
    )

    for _ in range(2):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        # 401 (wrong credentials) is expected and fine -- what matters is
        # that the rate limiter, not auth, decides the third request.
        assert response.status_code in (401, 422)

    limited = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )

    assert limited.status_code == 429


@pytest.mark.asyncio
async def test_a_default_tier_route_in_the_real_app_is_not_auth_limited(
    authed_client,
    real_app_limiter,
):
    """`/api/v1/companies` carries DEFAULT_TIER, and default is generous.

    A handful of requests -- far below the real default limit -- must never
    trip anything, proving the wiring did not accidentally attach the
    strict auth tier to an ordinary CRM route.
    """

    for _ in range(3):
        response = await authed_client.get("/api/v1/companies/")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_unreachable_yields_200_not_500_over_a_real_request():
    """Step 5's actual claim, proved end to end rather than at the function level.

    Unit tests already cover `_FailOpenRateLimiter.__call__` catching a
    `RedisError` directly; this proves the same thing survives FastAPI's own
    dependency resolution and exception handling, over a real ASGI request.

    Its own inline setup rather than `real_app_limiter`: this deliberately
    never lets `init_rate_limiter()` succeed, so it needs `FastAPILimiter`'s
    class attributes wired by hand instead.
    """

    import redis.exceptions
    from unittest.mock import AsyncMock, MagicMock

    from app.api.rate_limit import FastAPILimiter, _identifier

    app = _probe_app()

    broken = MagicMock()
    broken.evalsha = AsyncMock(
        side_effect=redis.exceptions.ConnectionError("connection refused")
    )

    app.dependency_overrides[AUTH_TIER] = _FailOpenRateLimiter(
        tier="test-broken", times=1, seconds=60
    )

    FastAPILimiter.redis = broken
    FastAPILimiter.lua_sha = "deadbeef"
    FastAPILimiter.identifier = _identifier

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, client=("198.51.100.42", 1)),
            base_url="http://test",
        ) as client:
            response = await client.get("/probe/auth")

        assert response.status_code == 200
    finally:
        await reset_rate_limiter()
