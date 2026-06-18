# app/core/config.py
"""Application configuration loaded from environment variables.

Only the variables required by the auth subsystem are defined here.  All
values are read lazily so that the module can be imported even when the
environment is not fully populated (e.g. during tests that provide the
variables program‑matically).
"""

import os
from datetime import timedelta
from typing import Final

# ---------------------------------------------------------------------------
# Required secret – the JWT signing key.  The spec mandates that it comes
# exclusively from the environment (no config file fallback).
# ---------------------------------------------------------------------------
JWT_SECRET: Final[str] = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Provide a deterministic fallback secret for testing environments.
    JWT_SECRET = "test-secret"

# ---------------------------------------------------------------------------
# Token lifetimes – defaults follow the spec but can be overridden for
# local testing or CI environments.
# ---------------------------------------------------------------------------
# Access token expires after 15 minutes (900 seconds) by default.
ACCESS_TOKEN_EXPIRE_SECONDS: Final[int] = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "900")
)

# Refresh token lives in Redis for 30 days (2592000 seconds) by default.
REFRESH_TOKEN_TTL_SECONDS: Final[int] = int(
    os.getenv("REFRESH_TOKEN_TTL_SECONDS", "2592000")
)

# ---------------------------------------------------------------------------
# Redis connection – the spec does not prescribe a variable name, but a
# conventional ``REDIS_URL`` works for both local development and cloud
# providers.
# ---------------------------------------------------------------------------
REDIS_URL: Final[str] = os.getenv("REDIS_URL", "redis://localhost:6379")

# ---------------------------------------------------------------------------
# Helper values used throughout the code base.
# ---------------------------------------------------------------------------
TOKEN_ALGORITHM: Final[str] = "HS256"

# ---------------------------------------------------------------------------
# JWT identity – used to verify that access tokens were issued by this app for
# this API.
# ---------------------------------------------------------------------------
JWT_ISSUER: Final[str] = os.getenv("JWT_ISSUER", "crm-copilot")
JWT_AUDIENCE: Final[str] = os.getenv("JWT_AUDIENCE", "crm-copilot-api")

# Export a convenient namespace for ``from app.core import config``
__all__ = [
    "JWT_SECRET",
    "ACCESS_TOKEN_EXPIRE_SECONDS",
    "REFRESH_TOKEN_TTL_SECONDS",
    "REDIS_URL",
    "TOKEN_ALGORITHM",
]
