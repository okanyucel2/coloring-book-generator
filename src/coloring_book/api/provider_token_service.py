"""Database-backed provider token management for Project001.

Wraps auth_core.TokenEncryption with SQLAlchemy persistence via the
ProviderToken model. Drop-in replacement for auth_flows.ProviderTokenManager
using real database storage instead of in-memory dict.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_core.encryption import TokenEncryption
from auth_core.exceptions import ProviderNotLinkedError

from .models import ProviderToken


@dataclass
class ProviderTokenData:
    """Decrypted provider tokens returned to callers."""
    access_token: str
    refresh_token: str | None = None
    scopes: dict | None = None
    expires_at: datetime | None = None
    provider_metadata: dict | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now >= expires


@dataclass
class ProviderInfo:
    """Summary info about a linked provider."""
    provider: str
    scopes: dict | None = None
    expires_at: datetime | None = None
    provider_metadata: dict | None = None
    is_expired: bool = False


RefreshFn = Callable[[str], Awaitable[dict[str, Any]]]


class DbProviderTokenManager:
    """CRUD + auto-refresh for encrypted provider tokens, persisted to database."""

    def __init__(
        self,
        encryption: TokenEncryption,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._encryption = encryption
        self._session_factory = session_factory

    async def store_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str | None = None,
        scopes: dict | None = None,
        expires_at: datetime | None = None,
        provider_metadata: dict | None = None,
    ) -> str:
        """Store (or upsert) encrypted provider tokens."""
        encrypted_access = self._encryption.encrypt(access_token)
        encrypted_refresh = (
            self._encryption.encrypt(refresh_token) if refresh_token else None
        )
        now = datetime.now(timezone.utc)

        async with self._session_factory() as db:
            result = await db.execute(
                select(ProviderToken).where(
                    and_(
                        ProviderToken.user_id == user_id,
                        ProviderToken.provider == provider,
                    )
                )
            )
            existing = result.scalars().first()

            if existing:
                existing.encrypted_access_token = encrypted_access
                existing.encrypted_refresh_token = encrypted_refresh
                existing.scopes = scopes
                existing.expires_at = expires_at
                existing.provider_metadata = provider_metadata
                existing.updated_at = now
                await db.commit()
                return existing.id

            record = ProviderToken(
                id=str(uuid4()),
                user_id=user_id,
                provider=provider,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                scopes=scopes,
                expires_at=expires_at,
                provider_metadata=provider_metadata,
                created_at=now,
            )
            db.add(record)
            await db.commit()
            return record.id

    async def get_tokens(
        self, user_id: str, provider: str
    ) -> ProviderTokenData | None:
        """Get decrypted provider tokens."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(ProviderToken).where(
                    and_(
                        ProviderToken.user_id == user_id,
                        ProviderToken.provider == provider,
                    )
                )
            )
            record = result.scalars().first()

        if record is None:
            return None

        access_token = self._encryption.decrypt(record.encrypted_access_token)
        refresh_token = (
            self._encryption.decrypt(record.encrypted_refresh_token)
            if record.encrypted_refresh_token
            else None
        )

        return ProviderTokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=record.scopes,
            expires_at=record.expires_at,
            provider_metadata=record.provider_metadata,
        )

    async def delete_tokens(self, user_id: str, provider: str) -> bool:
        """Delete provider tokens for a user."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(ProviderToken).where(
                    and_(
                        ProviderToken.user_id == user_id,
                        ProviderToken.provider == provider,
                    )
                )
            )
            record = result.scalars().first()
            if record is None:
                return False

            await db.delete(record)
            await db.commit()
            return True

    async def refresh_if_expired(
        self,
        user_id: str,
        provider: str,
        refresh_fn: RefreshFn,
    ) -> ProviderTokenData:
        """Get tokens, refreshing them if expired."""
        tokens = await self.get_tokens(user_id, provider)
        if tokens is None:
            raise ProviderNotLinkedError(
                f"No tokens found for provider '{provider}'"
            )

        if not tokens.is_expired:
            return tokens

        if not tokens.refresh_token:
            raise ProviderNotLinkedError(
                f"Token expired and no refresh token for provider '{provider}'"
            )

        new_tokens = await refresh_fn(tokens.refresh_token)

        await self.store_tokens(
            user_id=user_id,
            provider=provider,
            access_token=new_tokens["access_token"],
            refresh_token=new_tokens.get("refresh_token", tokens.refresh_token),
            scopes=tokens.scopes,
            expires_at=new_tokens.get("expires_at", tokens.expires_at),
            provider_metadata=tokens.provider_metadata,
        )

        return await self.get_tokens(user_id, provider)  # type: ignore[return-value]

    async def list_providers(self, user_id: str) -> list[ProviderInfo]:
        """List all linked providers for a user."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(ProviderToken).where(ProviderToken.user_id == user_id)
            )
            records = result.scalars().all()

        providers = []
        for record in records:
            is_expired = False
            if record.expires_at is not None:
                now = datetime.now(timezone.utc)
                exp = record.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                is_expired = now >= exp

            providers.append(
                ProviderInfo(
                    provider=record.provider,
                    scopes=record.scopes,
                    expires_at=record.expires_at,
                    provider_metadata=record.provider_metadata,
                    is_expired=is_expired,
                )
            )
        return providers
