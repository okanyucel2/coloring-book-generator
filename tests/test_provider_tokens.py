"""Tests for ProviderToken model and DbProviderTokenManager."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth_core.encryption import TokenEncryption
from auth_core.exceptions import ProviderNotLinkedError
from coloring_book.api.models import Base, ProviderToken, User
from coloring_book.api.provider_token_service import (
    DbProviderTokenManager,
    ProviderTokenData,
)


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture
def encryption():
    return TokenEncryption(TokenEncryption.generate_key())


@pytest.fixture
def manager(encryption, session_factory):
    return DbProviderTokenManager(encryption=encryption, session_factory=session_factory)


@pytest.fixture
async def user(db) -> User:
    u = User(id=str(uuid.uuid4()), email="test@example.com", name="Test User")
    db.add(u)
    await db.commit()
    return u


# ---------------------------------------------------------------------------
# ProviderToken Model
# ---------------------------------------------------------------------------

class TestProviderTokenModel:
    async def test_create_provider_token(self, db, user, encryption):
        """ProviderToken can be created with encrypted data."""
        token = ProviderToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="etsy",
            encrypted_access_token=encryption.encrypt("access-123"),
            encrypted_refresh_token=encryption.encrypt("refresh-456"),
            scopes={"scope": "listings_r"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            provider_metadata={"shop_id": "99"},
            created_at=datetime.now(timezone.utc),
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)

        assert token.id is not None
        assert token.user_id == user.id
        assert token.provider == "etsy"
        assert b"access-123" not in token.encrypted_access_token

    async def test_unique_constraint_user_provider(self, db, user, encryption):
        """Only one token row per (user_id, provider) pair."""
        from sqlalchemy.exc import IntegrityError

        t1 = ProviderToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="etsy",
            encrypted_access_token=encryption.encrypt("tok1"),
        )
        db.add(t1)
        await db.commit()

        t2 = ProviderToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="etsy",
            encrypted_access_token=encryption.encrypt("tok2"),
        )
        db.add(t2)
        with pytest.raises(IntegrityError):
            await db.commit()


# ---------------------------------------------------------------------------
# DbProviderTokenManager
# ---------------------------------------------------------------------------

class TestDbProviderTokenManager:
    async def test_store_and_get_tokens(self, manager, user):
        """Store tokens and retrieve them decrypted."""
        await manager.store_tokens(
            user_id=user.id,
            provider="etsy",
            access_token="access-abc",
            refresh_token="refresh-xyz",
            scopes={"scope": "listings_r"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            provider_metadata={"shop_id": "42"},
        )

        tokens = await manager.get_tokens(user.id, "etsy")
        assert tokens is not None
        assert tokens.access_token == "access-abc"
        assert tokens.refresh_token == "refresh-xyz"
        assert tokens.scopes == {"scope": "listings_r"}
        assert tokens.provider_metadata == {"shop_id": "42"}

    async def test_get_nonexistent_returns_none(self, manager, user):
        result = await manager.get_tokens(user.id, "github")
        assert result is None

    async def test_upsert_overwrites_existing(self, manager, user):
        await manager.store_tokens(user.id, "etsy", access_token="old")
        await manager.store_tokens(user.id, "etsy", access_token="new")

        tokens = await manager.get_tokens(user.id, "etsy")
        assert tokens.access_token == "new"

    async def test_delete_tokens(self, manager, user):
        await manager.store_tokens(user.id, "etsy", access_token="del-me")
        result = await manager.delete_tokens(user.id, "etsy")
        assert result is True

        tokens = await manager.get_tokens(user.id, "etsy")
        assert tokens is None

    async def test_delete_nonexistent_returns_false(self, manager, user):
        result = await manager.delete_tokens(user.id, "github")
        assert result is False

    async def test_list_providers(self, manager, user):
        await manager.store_tokens(user.id, "etsy", access_token="a")
        await manager.store_tokens(user.id, "github", access_token="b")

        providers = await manager.list_providers(user.id)
        names = {p.provider for p in providers}
        assert names == {"etsy", "github"}

    async def test_list_providers_empty(self, manager, user):
        providers = await manager.list_providers(user.id)
        assert providers == []

    async def test_tokens_are_encrypted_in_db(self, manager, user, session_factory):
        """Raw stored values are encrypted, not plaintext."""
        await manager.store_tokens(user.id, "etsy", access_token="secret-value")

        from sqlalchemy import select, and_

        async with session_factory() as db:
            result = await db.execute(
                select(ProviderToken).where(
                    and_(
                        ProviderToken.user_id == user.id,
                        ProviderToken.provider == "etsy",
                    )
                )
            )
            record = result.scalars().first()

        assert record is not None
        assert b"secret-value" not in record.encrypted_access_token

    async def test_refresh_if_expired_calls_refresh_fn(self, manager, user):
        await manager.store_tokens(
            user.id, "etsy",
            access_token="old-access",
            refresh_token="my-refresh",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        async def mock_refresh(refresh_token):
            assert refresh_token == "my-refresh"
            return {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            }

        tokens = await manager.refresh_if_expired(user.id, "etsy", mock_refresh)
        assert tokens.access_token == "new-access"
        assert tokens.refresh_token == "new-refresh"

    async def test_refresh_if_not_expired_returns_cached(self, manager, user):
        await manager.store_tokens(
            user.id, "etsy",
            access_token="valid-access",
            refresh_token="my-refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        async def should_not_be_called(rt):
            raise AssertionError("refresh_fn should not be called")

        tokens = await manager.refresh_if_expired(user.id, "etsy", should_not_be_called)
        assert tokens.access_token == "valid-access"

    async def test_refresh_nonexistent_raises(self, manager, user):
        async def noop(rt):
            return {}

        with pytest.raises(ProviderNotLinkedError):
            await manager.refresh_if_expired(user.id, "etsy", noop)

    async def test_store_without_refresh_token(self, manager, user):
        await manager.store_tokens(user.id, "etsy", access_token="access-only")
        tokens = await manager.get_tokens(user.id, "etsy")
        assert tokens.access_token == "access-only"
        assert tokens.refresh_token is None


# ---------------------------------------------------------------------------
# ProviderTokenData
# ---------------------------------------------------------------------------

class TestProviderTokenData:
    def test_is_expired_no_expiry(self):
        data = ProviderTokenData(access_token="t", expires_at=None)
        assert data.is_expired is False

    def test_is_expired_future(self):
        data = ProviderTokenData(
            access_token="t",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert data.is_expired is False

    def test_is_expired_past(self):
        data = ProviderTokenData(
            access_token="t",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert data.is_expired is True
