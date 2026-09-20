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

async def reset_redis() -> None:
    """Close the cached client and drop it.

    The client owns a connection pool bound to the event loop that created it.
    A process with a single loop never notices, but anything that creates a new
    loop -- the test suite makes one per test -- would otherwise reuse a pool
    tied to a closed loop and fail in teardown. Call this on shutdown, and
    between tests.
    """

    global _redis_instance

    if _redis_instance is not None:
        try:
            await _redis_instance.aclose()
        except Exception:
            # Teardown must not mask the real failure in the test or request.
            pass

        _redis_instance = None


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
