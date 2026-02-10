"""
Auth integration tests for project001 (coloring book generator).

Tests that auth-fastapi integrates correctly when mounted into the project001 app:
- Login endpoint exists and redirects
- OAuth callback creates users (mocked Authlib)
- Refresh token flow
- /auth/me returns user profile
- /auth/logout works
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.sessions import SessionMiddleware

from auth_core.jwt_manager import create_token_pair
from auth_fastapi import AuthConfig, create_auth_router, register_auth_exception_handlers
from src.coloring_book.api.models import Base, User

JWT_SECRET = "test-secret-key-that-is-at-least-32-chars-long!"


@pytest.fixture
def auth_config() -> AuthConfig:
    return AuthConfig(
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        jwt_secret=JWT_SECRET,
        frontend_url="http://localhost:5173",
        backend_url="http://localhost:5000",
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
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture
def get_db(session_factory):
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session
    return _get_db


@pytest.fixture
def app(auth_config, get_db) -> FastAPI:
    """Build a minimal FastAPI app with auth router mounted, using project001's User model."""
    application = FastAPI()
    application.add_middleware(SessionMiddleware, secret_key=auth_config.effective_session_secret)
    register_auth_exception_handlers(application)
    router = create_auth_router(auth_config, User, get_db)
    application.include_router(router, prefix="/auth")
    return application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac


def _tokens(user_id: str, email: str = "u@test.com") -> dict:
    return create_token_pair(user_id, email, JWT_SECRET)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLoginGoogle:
    async def test_login_endpoint_exists(self, client):
        """GET /auth/login/google should exist (Authlib OIDC discovery will fail in test)."""
        r = await client.get("/auth/login/google")
        # Authlib tries to fetch Google OIDC config, which fails without network.
        # We accept redirect (302/307) or server error (500) — not 404.
        assert r.status_code in (302, 307, 500)


# ---------------------------------------------------------------------------
# Callback (mocked Authlib)
# ---------------------------------------------------------------------------

class TestCallbackGoogle:
    async def test_callback_creates_new_user(self, auth_config, get_db, db_session):
        """Mocked callback should create a user and redirect with JWT tokens."""
        mock_token = {
            "userinfo": {
                "sub": "google-abc123",
                "email": "artist@coloring.com",
                "name": "Artist User",
                "picture": "https://photo.url/artist.jpg",
            }
        }

        with patch("auth_fastapi.router.OAuth", autospec=True) as PatchedOAuth:
            mock_instance = MagicMock()
            mock_google = AsyncMock()
            mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
            mock_instance.google = mock_google
            PatchedOAuth.return_value = mock_instance

            app = FastAPI()
            app.add_middleware(SessionMiddleware, secret_key=auth_config.effective_session_secret)
            register_auth_exception_handlers(app)
            router = create_auth_router(auth_config, User, get_db)
            app.include_router(router, prefix="/auth")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
                r = await ac.get("/auth/callback/google")

        assert r.status_code == 302
        location = r.headers["location"]
        assert "oauth-callback" in location
        assert "access_token=" in location

        # Verify user data in redirect fragment
        fragment = location.split("#")[1]
        params = dict(p.split("=", 1) for p in fragment.split("&") if "=" in p)
        user_json = json.loads(unquote(params.get("user", "{}")))
        assert user_json["email"] == "artist@coloring.com"
        assert user_json["name"] == "Artist User"

    async def test_callback_updates_existing_user(self, auth_config, get_db, db_session):
        """Existing user should get name/avatar updated, not duplicated."""
        uid = str(uuid.uuid4())
        existing = User(
            id=uid, email="existing@coloring.com", name="Old Name",
            provider="google", provider_id="google-456",
        )
        db_session.add(existing)
        await db_session.commit()

        mock_token = {
            "userinfo": {
                "sub": "google-456",
                "email": "existing@coloring.com",
                "name": "Updated Name",
                "picture": "https://new.avatar/pic.jpg",
            }
        }

        with patch("auth_fastapi.router.OAuth", autospec=True) as PatchedOAuth:
            mock_instance = MagicMock()
            mock_google = AsyncMock()
            mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
            mock_instance.google = mock_google
            PatchedOAuth.return_value = mock_instance

            app = FastAPI()
            app.add_middleware(SessionMiddleware, secret_key=auth_config.effective_session_secret)
            router = create_auth_router(auth_config, User, get_db)
            app.include_router(router, prefix="/auth")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
                r = await ac.get("/auth/callback/google")

        assert r.status_code == 302

        await db_session.refresh(existing)
        assert existing.name == "Updated Name"
        assert existing.avatar_url == "https://new.avatar/pic.jpg"


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    async def test_valid_refresh_returns_new_tokens(self, client, db_session):
        uid = str(uuid.uuid4())
        user = User(id=uid, email="refresh@test.com", name="Refresh User")
        db_session.add(user)
        await db_session.commit()

        tokens = _tokens(uid, "refresh@test.com")
        r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_refresh_with_garbage_token_fails(self, client):
        r = await client.post("/auth/refresh", json={"refresh_token": "garbage"})
        assert r.status_code == 401

    async def test_refresh_with_access_token_fails(self, client, db_session):
        uid = str(uuid.uuid4())
        user = User(id=uid, email="wrong@test.com", name="Wrong")
        db_session.add(user)
        await db_session.commit()

        tokens = _tokens(uid, "wrong@test.com")
        r = await client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
        assert r.status_code == 401

    async def test_refresh_nonexistent_user_fails(self, client):
        tokens = _tokens(str(uuid.uuid4()), "ghost@test.com")
        r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------

class TestMe:
    async def test_me_returns_user_profile(self, client, db_session):
        uid = str(uuid.uuid4())
        user = User(
            id=uid, email="me@coloring.com", name="Artist",
            avatar_url="https://img.url/me.jpg", provider="google",
        )
        db_session.add(user)
        await db_session.commit()

        tokens = _tokens(uid, "me@coloring.com")
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "me@coloring.com"
        assert body["name"] == "Artist"
        assert body["id"] == uid
        assert body["avatar_url"] == "https://img.url/me.jpg"

    async def test_me_unauthenticated_returns_401(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    async def test_logout_returns_success(self, client):
        r = await client.post("/auth/logout")
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out successfully"
