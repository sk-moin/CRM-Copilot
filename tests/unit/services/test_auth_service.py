"""Unit tests for ``app.services.auth_service.AuthService``.

The tests exercise the core business‑logic functions without involving FastAPI
routers or Pydantic schemas, exactly as required by the task.
"""

import uuid
import json
import pytest
import pytest_asyncio
from custom_jwt import jwt
from redis.asyncio import Redis

from app.core import config
from app.core.redis_client import get_redis, token_hash
from app.core.security import decode_jwt
from app.services.auth_service import AuthService, get_auth_service
from app.services.exceptions import (
    DuplicateEmailError,
    DuplicateSubdomainError,
    InvalidCredentialsError,
    UserNotFoundError,
)

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def clean_redis():
    """Flush Redis before each test to avoid cross‑test interference."""
    client: Redis = get_redis()
    await client.flushdb()
    yield
    await client.flushdb()

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(async_session):
    service = get_auth_service(async_session)
    result = await service.register(
        email="alice@example.com",
        password="StrongPass!23",
        subdomain="acme",
        org_name="Acme Corp",
    )
    # Tokens should be present
    assert "access_token" in result and "refresh_token" in result

    # Verify that the refresh token hash is stored in Redis
    redis = get_redis()
    key = f"refresh:{token_hash(result['refresh_token'])}"
    stored = await redis.get(key)
    assert stored is not None
    payload = json.loads(stored)
    assert payload["user_id"]  # contains a UUID string

    # Verify that tenant, organization, user rows exist via a fresh query
    # (SQLAlchemy async session is still open; we can query directly)
    from packages.database.models import Tenant, Organization, User
    tenant = await async_session.get(Tenant, payload["tenant_id"])
    assert tenant is not None
    org = await async_session.get(Organization, payload["org_id"])
    assert org is not None
    user = await async_session.get(User, payload["user_id"])
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.role == "OWNER"

@pytest.mark.asyncio
async def test_register_duplicate_email(async_session):
    service = get_auth_service(async_session)
    await service.register(
        email="bob@example.com",
        password="pwd",
        subdomain="bobco",
        org_name="Bob Co",
    )
    with pytest.raises(DuplicateEmailError):
        await service.register(
            email="bob@example.com",
            password="pwd2",
            subdomain="bobco2",
            org_name="Bob Co 2",
        )

@pytest.mark.asyncio
async def test_register_duplicate_subdomain(async_session):
    service = get_auth_service(async_session)
    await service.register(
        email="c1@example.com",
        password="pwd",
        subdomain="dup",
        org_name="First",
    )
    with pytest.raises(DuplicateSubdomainError):
        await service.register(
            email="c2@example.com",
            password="pwd",
            subdomain="dup",
            org_name="Second",
        )

@pytest.mark.asyncio
async def test_login_success(async_session):
    service = get_auth_service(async_session)
    # First register a user
    await service.register(
        email="dave@example.com",
        password="SecRet123",
        subdomain="daveco",
        org_name="Dave Co",
    )
    # Now login
    result = await service.login(email="dave@example.com", password="SecRet123")
    assert "access_token" in result and "refresh_token" in result

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_session):
    service = get_auth_service(async_session)
    await service.register(
        email="eve@example.com",
        password="Correct1",
        subdomain="eveco",
        org_name="Eve Co",
    )
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="eve@example.com", password="WrongPass")
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="nonexistent@example.com", password="Whatever")

@pytest.mark.asyncio
async def test_refresh_single_use(async_session):
    service = get_auth_service(async_session)
    reg = await service.register(
        email="frank@example.com",
        password="Pass123!",
        subdomain="frankco",
        org_name="Frank Co",
    )
    first = await service.refresh(reg["refresh_token"])
    assert "access_token" in first and "refresh_token" in first
    # Reusing the same original token must fail
    with pytest.raises(InvalidCredentialsError):
        await service.refresh(reg["refresh_token"])
    # The new token can be used once
    second = await service.refresh(first["refresh_token"])
    assert "access_token" in second and "refresh_token" in second
    # And cannot be reused again
    with pytest.raises(InvalidCredentialsError):
        await service.refresh(first["refresh_token"])

@pytest.mark.asyncio
async def test_get_profile(async_session):
    service = get_auth_service(async_session)
    reg = await service.register(
        email="gina@example.com",
        password="Pwd!",
        subdomain="ginaco",
        org_name="Gina Co",
    )
    profile = await service.get_profile(reg["access_token"])
    # The profile must contain the required fields
    for key in ["id", "email", "role", "org_id", "tenant_id", "created_at"]:
        assert key in profile
    assert profile["email"] == "gina@example.com"
    assert profile["role"] == "OWNER"


@pytest.mark.asyncio
async def test_access_token_contains_iss_and_aud(async_session):
    """Verify that the access token includes the mandatory iss and aud claims."""
    service = get_auth_service(async_session)
    reg = await service.register(
        email="issuer@example.com",
        password="password",
        subdomain="issuer-sub",
        org_name="Issuer Org",
    )
    # Decode without verification to inspect payload
    raw_payload = jwt.decode(
        reg["access_token"],
        config.JWT_SECRET,
        algorithms=[config.TOKEN_ALGORITHM],
        options={"verify_aud": False, "verify_iss": False},
    )
    assert raw_payload["iss"] == config.JWT_ISSUER
    assert raw_payload["aud"] == config.JWT_AUDIENCE


@pytest.mark.asyncio
async def test_token_validation_rejects_incorrect_issuer(async_session):
    """Token with wrong issuer must be rejected."""
    from custom_jwt import JWTError

    service = get_auth_service(async_session)
    reg = await service.register(
        email="wrong-iss@example.com",
        password="password",
        subdomain="wrong-iss-sub",
        org_name="Wrong Issuer Org",
    )
    # Create a token with a manipulated issuer claim
    legitimate = jwt.decode(
        reg["access_token"],
        config.JWT_SECRET,
        algorithms=[config.TOKEN_ALGORITHM],
        options={"verify_aud": False, "verify_iss": False},
    )
    # Create a minimal JWT with wrong issuer using the stub
    wrong_iss_token = jwt.encode(
        {
            **legitimate,
            "iss": "malicious-issuer",
        },
        config.JWT_SECRET,
        algorithm=config.TOKEN_ALGORITHM,
    )
    with pytest.raises(JWTError):
        decode_jwt(wrong_iss_token)


@pytest.mark.asyncio
async def test_token_validation_rejects_incorrect_audience(async_session):
    """Token with wrong audience must be rejected."""
    from custom_jwt import JWTError

    service = get_auth_service(async_session)
    reg = await service.register(
        email="wrong-aud@example.com",
        password="password",
        subdomain="wrong-aud-sub",
        org_name="Wrong Audience Org",
    )
    legitimate = jwt.decode(
        reg["access_token"],
        config.JWT_SECRET,
        algorithms=[config.TOKEN_ALGORITHM],
        options={"verify_aud": False, "verify_iss": False},
    )
    wrong_aud_token = jwt.encode(
        {
            **legitimate,
            "aud": "malicious-audience",
        },
        config.JWT_SECRET,
        algorithm=config.TOKEN_ALGORITHM,
    )
    with pytest.raises(JWTError):
        decode_jwt(wrong_aud_token)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def close_redis():
    # Ensure Redis client is closed after the entire suite
    client = get_redis()
    yield
    await client.close()
