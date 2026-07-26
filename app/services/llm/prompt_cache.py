"""Prompt cache abstraction.

Provides a lightweight cache for rendered prompt templates.
The default implementation is an in-memory cache suitable for
development and testing. It can later be replaced with Redis
without affecting PromptManager.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class PromptCache(ABC):
    """Abstract prompt cache."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Return cached prompt or None."""

    @abstractmethod
    async def set(
        self,
        key: str,
        value: str,
    ) -> None:
        """Store prompt in cache."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a cached prompt."""

    @abstractmethod
    async def clear(self) -> None:
        """Clear the cache."""


class InMemoryPromptCache(PromptCache):
    """
    Simple in-memory cache.

    Intended for development, unit tests, and environments
    where Redis is unavailable.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    async def set(
        self,
        key: str,
        value: str,
    ) -> None:
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def clear(self) -> None:
        self._cache.clear()


# Default cache implementation.
prompt_cache: PromptCache = InMemoryPromptCache()