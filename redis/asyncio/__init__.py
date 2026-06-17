"""Very small stub of ``redis.asyncio`` used for unit testing.

The real project expects an async Redis client with a subset of methods:
* ``set`` (supports ``ex`` expiration argument, ignored here)
* ``get``
* ``delete``
* ``flushdb``
* ``close``

This stub stores data in a plain in‑memory ``dict`` and implements the
corresponding async methods. It is sufficient for the AuthService tests and
does not require the external ``redis`` package.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict


class Redis:
    """In‑memory async Redis client stub.

    All operations are ``async`` but execute synchronously because the data is
    stored in a class‑level dictionary. The ``decode_responses`` argument is
    accepted for API compatibility but ignored – values are always ``str``.
    """

    _store: Dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        # Accept any args/kwargs to match the real client signature.
        self.decode_responses = kwargs.get("decode_responses", False)

    @classmethod
    def from_url(cls, url: str, decode_responses: bool = False) -> "Redis":
        # ``url`` is ignored – we always create a singleton in‑process client.
        return cls(decode_responses=decode_responses)

    # ---------------------------------------------------------------------
    # Async Redis commands used by the codebase
    # ---------------------------------------------------------------------
    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    async def flushdb(self) -> bool:
        self._store.clear()
        return True

    async def close(self) -> None:
        # No resources to release in the stub.
        return None
