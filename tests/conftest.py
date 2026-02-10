"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def project_dir():
    """Return project root directory"""
    return project_root


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide temporary output directory for tests"""
    return tmp_path / "output"


# ---------------------------------------------------------------------------
# Async DB fixtures for API tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def async_engine():
    """Create an async in-memory SQLite engine with all tables."""
    from coloring_book.api.models import Base

    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def async_session_factory(async_engine):
    """Create an async session factory bound to the test engine."""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def override_get_db(async_session_factory):
    """Return an async get_db override for FastAPI dependency injection."""
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            yield session
    return _get_db
