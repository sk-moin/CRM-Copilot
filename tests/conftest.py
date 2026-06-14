"""Test fixtures for async SQLAlchemy with PostgreSQL.

The fixture creates a single async engine using ``asyncpg`` and provides an
``AsyncSession`` that is rolled back after each test to keep the database clean.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Ensure the project root is on the Python path so imports like
# ``from packages.database.models import ...`` work inside the test suite.
import sys
from pathlib import Path

# ``tests/conftest.py`` lives in ``<repo>/tests``; the parent of that is the repo root.
repo_root = Path(__file__).resolve().parents[0].parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Database URL – force asyncpg driver for test suite (ignores env var to ensure async driver).
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_copilot"

# Create a single engine for the entire test session (reuse connections).


@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an ``AsyncSession`` rolled back after each test.

    This fixture now creates a fresh async engine for each test function, which
    avoids cross‑test event‑loop / connection‑pool issues. The lifecycle is:

    1. ``engine = create_async_engine(DATABASE_URL, echo=False)`` – a new engine
       (and its connection pool) tied to the current test’s event loop.
    2. ``async with engine.connect() as conn`` – acquire a raw connection.
    3. ``await conn.begin()`` – start a single transaction.
    4. ``session = AsyncSession(conn, expire_on_commit=False)`` – bind the
       session to that connection; the session does not start another
       transaction because one already exists.
    5. ``yield session`` – the test runs.
    6. ``await conn.rollback()`` – undo everything the test did.
    7. ``await engine.dispose()`` – cleanly shut down the engine’s pool.

    This pattern ensures each test runs with its own isolated engine and event
    loop, eliminating the “Event loop is closed” error you observed.
    """
    # Step 1 – create a fresh engine for this test.
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        # Step 2‑3 – start a transaction on the connection.
        await conn.begin()
        # Step 4 – bind an AsyncSession to the connection.
        session = AsyncSession(conn, expire_on_commit=False)
        # Step 5 – hand the session to the test.
        yield session
        # Step 6 – roll back changes.
        await conn.rollback()
    # Step 7 – dispose of the engine (closes the pool tied to the loop).
    await engine.dispose()
