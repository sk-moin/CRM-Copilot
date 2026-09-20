# app/core/security.py
"""Security utilities for the CRM‑Copilot backend.

This module centralises all cryptographic operations required by Spec 001:

* Password hashing/verification using **bcrypt** directly.
* JWT creation and validation using **PyJWT**.
* Refresh‑token generation, parsing and rotation.  The refresh token has the
  format ``<jti>.<random_secret>`` and is stored in Redis under the key
  ``refresh:{jti}`` (the Redis client lives in ``app.core.redis_client``).

The implementation deliberately avoids any direct DB access – ``get_current_user``
(and the FastAPI dependencies) will decode the JWT statelessly.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

import bcrypt
import jwt
from jwt import PyJWTError as JWTError

from app.core import config

# ---------------------------------------------------------------------------
# Password hashing – passlib provides a high‑level wrapper around bcrypt.
# ---------------------------------------------------------------------------
# Legacy hashes written by the stub that previously stood in for passlib:
# "bcrypt$" followed by an unsalted SHA-256 hex digest. They are recognised
# here only so existing accounts can still sign in and be upgraded in place on
# their next successful login. Remove this once no such hashes remain.
_LEGACY_STUB_PREFIX = "bcrypt$"


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash for ``password``."""

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def _is_legacy_stub_hash(hashed_password: str) -> bool:
    """True for the unsalted SHA-256 hashes the old stub produced.

    A real bcrypt hash starts with ``$2a$``/``$2b$``/``$2y$``, so the two
    formats cannot be confused despite the stub's misleading prefix.
    """

    if not hashed_password.startswith(_LEGACY_STUB_PREFIX):
        return False

    digest = hashed_password[len(_LEGACY_STUB_PREFIX):]

    return len(digest) == 64 and all(
        c in "0123456789abcdef" for c in digest.lower()
    )


def _verify_legacy_stub(plain_password: str, hashed_password: str) -> bool:
    import hashlib

    expected = hashlib.sha256(plain_password.encode()).hexdigest()

    return secrets.compare_digest(
        hashed_password,
        f"{_LEGACY_STUB_PREFIX}{expected}",
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify ``plain_password`` against a stored hash.

    Accepts a legacy stub hash so an existing account is not locked out by the
    move to real bcrypt. Call :func:`needs_rehash` after a successful check and
    re-store the password when it returns True.
    """

    if not hashed_password:
        return False

    if _is_legacy_stub_hash(hashed_password):
        return _verify_legacy_stub(plain_password, hashed_password)

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed or unrecognised hash: refuse rather than raise, so a bad
        # row cannot turn a failed login into a 500.
        return False


def needs_rehash(hashed_password: str) -> bool:
    """True when a stored hash should be replaced on the next successful login."""

    return _is_legacy_stub_hash(hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers – all JWT operations use the secret from ``config.JWT_SECRET``
# and the HS256 algorithm.  The ``jti`` claim is always generated freshly.
# ---------------------------------------------------------------------------

def _generate_jti() -> str:
    """Create a new UUID4 string to be used as the JWT ID (jti)."""

    return str(uuid.uuid4())


def create_access_token(
    *,
    user_id: str | uuid.UUID,
    tenant_id: str | uuid.UUID,
    org_id: str | uuid.UUID,
    email: str,
    role: str,
) -> str:
    """Create a signed JWT access token.

    The token includes the mandatory claims required by the spec:

    * ``sub`` – the user ID.
    * ``jti`` – a freshly generated UUID4.
    * ``tenant_id``
    * ``org_id``
    * ``role`` – stored as a plain string (the ``UserRole`` enum can be
      converted via ``.value`` before calling this function).
    * ``iss`` – token issuer (``config.JWT_ISSUER``).
    * ``aud`` – intended audience (``config.JWT_AUDIENCE``).
    * ``iat`` – issued-at timestamp.
    * ``exp`` – ``datetime.utcnow()`` plus ``config.ACCESS_TOKEN_EXPIRE_SECONDS``.
    """


    now = datetime.now(timezone.utc)

    expire = now + timedelta(seconds=config.ACCESS_TOKEN_EXPIRE_SECONDS)

    payload = {
        "sub": str(user_id),
        "jti": _generate_jti(),
        "tenant_id": str(tenant_id),
        "org_id": str(org_id),
        "role": role,
        "iss": config.JWT_ISSUER,
        "aud": config.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.TOKEN_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT, returning the payload.

    Verifies signature, expiration, issuer and audience. Raises ``JWTError`` if
    any verification step fails.
    """

    return jwt.decode(
        token,
        config.JWT_SECRET,
        algorithms=[config.TOKEN_ALGORITHM],
        audience=config.JWT_AUDIENCE,
        issuer=config.JWT_ISSUER,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": True,
            "verify_iss": True,
            "require": ["exp", "iat", "sub", "iss", "aud"],
        },
    )

# ---------------------------------------------------------------------------
# Refresh token utilities – the token format is ``<jti>.<random_secret>``.
# The ``jti`` part is also used as the Redis key ``refresh:{jti}``.
# ---------------------------------------------------------------------------

def create_refresh_token() -> str:
    """Generate a new refresh token string.

    A new ``jti`` is produced on every call (rotation on each refresh) and a
    cryptographically‑secure random secret is appended.  Example output:
    ``"550e8400-e29b-41d4-a716-446655440000.qhXz8Y3Kc5s87v4Y6t9U"``.
    """

    jti = _generate_jti()
    secret = secrets.token_urlsafe(32)
    return f"{jti}.{secret}"


def parse_refresh_token(token: str) -> Tuple[str, str]:
    """Split a refresh token into its ``jti`` and secret components.

    The function validates that the token contains exactly one ``.`` separating the
    two parts and returns ``(jti, secret)``.  ``ValueError`` is raised for a malformed
    token.
    """

    try:
        jti, secret = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Refresh token must be in the format '<jti>.<secret>'") from exc
    return jti, secret


__all__ = [
    "JWTError",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "create_access_token",
    "decode_jwt",
    "create_refresh_token",
    "parse_refresh_token",
]
