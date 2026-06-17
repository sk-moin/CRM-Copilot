"""Redis client helper for the authentication service.

Provides a singleton ``Redis`` instance configured from ``app.core.config`` and a
utility to hash refresh‑token values before storing them. Storing only the hash
prevents the raw token from ever being persisted, satisfying the spec's
security requirement.
"""

import hashlib
from typing import Final

from redis.asyncio import Redis

from app.core import config

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------
_redis_instance: Redis | None = None

def get_redis() -> Redis:
    """Return a global ``Redis`` client.

    The client is created on first call using ``REDIS_URL`` from the config.
    ``decode_responses=True`` makes ``get``/``set`` return ``str`` values.
    """
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = Redis.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_instance

# ---------------------------------------------------------------------------
# Helper for opaque‑token storage – store only a SHA‑256 hash of the token.
# ---------------------------------------------------------------------------
def token_hash(token: str) -> str:
    """Return a SHA‑256 hex digest of ``token``.

    The raw refresh token never touches Redis; only its hash is stored, so a
    leak of Redis data does not reveal usable tokens.
    """
    return hashlib.sha256(token.encode()).hexdigest()

# Export symbols
__all__: Final = ["get_redis", "token_hash"]
