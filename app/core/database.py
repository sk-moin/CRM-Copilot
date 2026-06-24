# app/core/database.py
"""Production database infrastructure for CRM‑Copilot.

Provides a single async SQLAlchemy engine, an async sessionmaker, and a
FastAPI‑compatible ``get_db`` dependency.  The module follows the same
environment conventions as Alembic and the test fixture, ensuring that the
default URL works out‑of‑the‑box for local development.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

# ---------------------------------------------------------------------------
# DATABASE_URL handling – read from the environment, fall back to the same
# default used by Alembic and the test suite.
# ---------------------------------------------------------------------------
DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot"
)

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# ---------------------------------------------------------------------------
# Async engine – a single global engine that will be shared across the
# application. ``future=True`` enables SQLAlchemy 2.x style usage.
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,  # set to True for debugging; keep quiet for normal runs
    future=True,
)

# ---------------------------------------------------------------------------
# Async sessionmaker – creates ``AsyncSession`` objects bound to the engine.
# ``expire_on_commit=False`` mirrors the pattern used in the test fixture.
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency – yields a fresh session per request and guarantees it
# is closed afterwards.
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Export the public symbols expected by the rest of the code base.
__all__ = ["engine", "AsyncSessionLocal", "get_db"]
