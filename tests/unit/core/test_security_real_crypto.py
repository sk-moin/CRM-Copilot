"""The auth primitives must be real, not stand-ins.

This repository previously tracked three stub packages at its root —
`passlib/`, `custom_jwt/` and `redis/` — that satisfied the imports in
`app/core/security.py` with toy implementations:

- passwords were unsalted SHA-256 prefixed with the literal string `bcrypt$`,
  so stored hashes looked like bcrypt and were not;
- tokens were a JSON blob signed with `sha256(payload + key)` rather than HMAC,
  and `exp` was never checked, so a token that expired a year ago was accepted;
- Redis was an in-memory fake, which is why the service was missing from
  docker-compose entirely.

These tests fail if any of that returns.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from app.core import config
from app.core.security import (
    JWTError,
    create_access_token,
    decode_jwt,
    hash_password,
    needs_rehash,
    verify_password,
)


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #


def test_hashes_are_real_bcrypt():
    hashed = hash_password("correct horse battery staple")

    # bcrypt's own prefix. The stub used a literal "bcrypt$".
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert not hashed.startswith("bcrypt$")


def test_hashes_are_salted():
    """The stub was deterministic, so the whole table fell to one rainbow table."""

    password = "correct horse battery staple"

    assert hash_password(password) != hash_password(password)


def test_a_hash_is_not_the_sha256_of_the_password():
    password = "correct horse battery staple"

    assert hashlib.sha256(password.encode()).hexdigest() not in hash_password(
        password
    )


def test_verification_round_trips():
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


@pytest.mark.parametrize("bad", ["", "not-a-hash", "bcrypt$short", "$2b$broken"])
def test_a_malformed_stored_hash_is_refused_not_raised(bad):
    """A bad row must fail the login, not turn it into a 500."""

    assert verify_password("anything", bad) is False


# --------------------------------------------------------------------------- #
# Legacy migration
# --------------------------------------------------------------------------- #


def _legacy(password: str) -> str:
    return "bcrypt$" + hashlib.sha256(password.encode()).hexdigest()


def test_a_legacy_stub_hash_still_signs_in():
    """Existing accounts are migrated on next login, not locked out."""

    assert verify_password("hunter2", _legacy("hunter2"))
    assert not verify_password("wrong", _legacy("hunter2"))


def test_a_legacy_hash_is_flagged_for_rehash():
    assert needs_rehash(_legacy("hunter2"))


def test_a_real_bcrypt_hash_is_not_flagged():
    assert not needs_rehash(hash_password("hunter2"))


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #


def _claims(**overrides) -> dict:
    now = datetime.now(UTC)
    claims = {
        "sub": "attacker",
        "jti": "forged",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": config.JWT_ISSUER,
        "aud": config.JWT_AUDIENCE,
    }
    claims.update(overrides)
    return claims


def _token(key: str | None = None, **overrides) -> str:
    return pyjwt.encode(
        _claims(**overrides),
        key or config.JWT_SECRET,
        algorithm="HS256",
    )


def test_a_valid_token_decodes():
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        org_id="33333333-3333-3333-3333-333333333333",
        email="user@example.com",
        role="ADMIN",
    )

    claims = decode_jwt(token)

    assert claims["sub"] == "11111111-1111-1111-1111-111111111111"
    assert claims["role"] == "ADMIN"


def test_tokens_are_real_jwts():
    """The stub emitted a JSON object, not a three-part JWT."""

    token = create_access_token(
        user_id="1",
        tenant_id="2",
        org_id="3",
        email="user@example.com",
        role="MEMBER",
    )

    assert token.count(".") == 2
    assert not token.startswith("{")


def test_an_expired_token_is_rejected():
    """The defect that mattered most: exp was never checked."""

    expired = _token(exp=datetime.now(UTC) - timedelta(days=365))

    with pytest.raises(JWTError):
        decode_jwt(expired)


def test_a_token_signed_with_the_wrong_key_is_rejected():
    with pytest.raises(JWTError):
        decode_jwt(_token(key="not-the-secret"))


def test_a_token_without_exp_is_rejected():
    claims = _claims()
    del claims["exp"]

    forged = pyjwt.encode(claims, config.JWT_SECRET, algorithm="HS256")

    with pytest.raises(JWTError):
        decode_jwt(forged)


def test_the_wrong_audience_is_rejected():
    with pytest.raises(JWTError):
        decode_jwt(_token(aud="some-other-service"))


def test_the_wrong_issuer_is_rejected():
    with pytest.raises(JWTError):
        decode_jwt(_token(iss="somebody-else"))


def test_an_unsigned_token_is_rejected():
    """alg=none must never be honoured."""

    unsigned = pyjwt.encode(_claims(), key="", algorithm="none")

    with pytest.raises(JWTError):
        decode_jwt(unsigned)
