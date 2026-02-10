"""Tests for Etsy OAuth flow — DB token persistence, callback HTML, postMessage.

Tests the end-to-end flow:
  auth-url → callback (GET) → HTMLResponse with postMessage → tokens in DB
  status reads from DB
  disconnect removes DB tokens
  tokens survive client recreation
  state race condition (concurrent OAuth flows)
"""

import os
import time
from unittest.mock import patch

import coloring_book.api.etsy_routes as etsy_routes_module
import pytest
from coloring_book.api import models
from coloring_book.api import workbook_routes as wr_module
from coloring_book.api.app import DEFAULT_USER_ID, app
from coloring_book.api.workbook_routes import _generation_tasks, _pdfs
from coloring_book.etsy.client import EtsyClient, TokenResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def db_session(monkeypatch):
    """Create a fresh in-memory SQLite database for each test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create default system user for FK constraint
    session = TestSession()
    session.add(models.User(
        id=DEFAULT_USER_ID,
        email="system@localhost",
        name="System",
        provider="system",
    ))
    session.commit()
    session.close()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[models.get_db] = override_get_db
    monkeypatch.setattr(wr_module, "SessionLocal", TestSession)

    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._pending_states.clear()

    yield TestSession

    app.dependency_overrides.clear()
    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._pending_states.clear()
    models.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


def _mock_exchange_code():
    """Create a mock for EtsyClient.exchange_code that returns valid tokens."""
    async def mock_exchange(self_or_code, code=None):
        # Handle both bound and unbound call styles
        tokens = TokenResponse(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_type="Bearer",
            expires_in=3600,
        )
        # If called as bound method, self_or_code is self
        if isinstance(self_or_code, EtsyClient):
            self_or_code.tokens = tokens
        return tokens
    return mock_exchange


def _mock_get_me():
    """Create a mock for EtsyClient.get_me that returns shop info."""
    async def mock_get_me(self):
        return {"user_id": 12345, "shop_id": 67890, "shop_name": "TestShop"}
    return mock_get_me


class TestCallbackReturnsHTML:
    """Verify the callback returns an HTML page with postMessage script."""

    def test_callback_returns_html_on_success(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Get auth URL to register a state
            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            # Mock exchange_code and get_me
            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                response = client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "valid_code", "state": state},
                )

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "etsy-oauth-complete" in response.text
            assert "success: true" in response.text
            assert "67890" in response.text  # shop_id
            assert "TestShop" in response.text  # shop_name

    def test_callback_returns_html_on_invalid_state(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            response = client.get(
                "/api/v1/etsy/callback",
                params={"code": "some_code", "state": "invalid_state"},
            )
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "success: false" in response.text

    def test_callback_returns_html_on_auth_error(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            # Mock exchange_code to raise an auth error
            from coloring_book.etsy.client import EtsyAuthError
            async def mock_fail(self, code):
                raise EtsyAuthError("Invalid code")

            with patch.object(EtsyClient, "exchange_code", mock_fail):
                response = client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "bad_code", "state": state},
                )

            assert response.status_code == 200
            assert "success: false" in response.text
            assert "Invalid code" in response.text


class TestCallbackStoresTokensInDB:
    """Verify that successful OAuth stores tokens that survive across requests."""

    def test_callback_stores_tokens_in_db(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Ensure clean state
            client.post("/api/v1/etsy/disconnect")

            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "valid_code", "state": state},
                )

            # Verify tokens persisted via status endpoint
            # (uses DbProviderTokenManager to read from DB)
            status = client.get("/api/v1/etsy/status").json()
            assert status["connected"] is True
            assert status["shop_id"] == 67890
            assert status["shop_name"] == "TestShop"

            # Verify tokens survive disconnect + reconnect cycle
            client.post("/api/v1/etsy/disconnect")
            assert client.get("/api/v1/etsy/status").json()["connected"] is False


class TestStatusReadsFromDB:
    """Verify status endpoint reads from DB, not in-memory client."""

    def test_status_connected_when_db_has_tokens(self, client, db_session):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # First connect via callback
            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "valid_code", "state": state},
                )

            # Now check status — should be connected from DB
            status_resp = client.get("/api/v1/etsy/status")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["connected"] is True
            assert data["shop_id"] == 67890
            assert data["shop_name"] == "TestShop"

    def test_status_not_connected_when_db_empty(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Ensure no tokens in DB
            client.post("/api/v1/etsy/disconnect")

            status_resp = client.get("/api/v1/etsy/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["connected"] is False


class TestDisconnectRemovesDBTokens:
    """Verify disconnect removes tokens from DB."""

    def test_disconnect_removes_db_tokens(self, client, db_session):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Connect first
            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "valid_code", "state": state},
                )

            # Verify connected
            assert client.get("/api/v1/etsy/status").json()["connected"] is True

            # Disconnect
            disc_resp = client.post("/api/v1/etsy/disconnect")
            assert disc_resp.status_code == 200
            assert "Disconnected" in disc_resp.json()["message"]

            # Verify DB token removed
            session = db_session()
            token = session.query(models.ProviderToken).filter(
                models.ProviderToken.provider == "etsy",
            ).first()
            session.close()
            assert token is None

            # Status should show disconnected
            assert client.get("/api/v1/etsy/status").json()["connected"] is False


class TestTokensSurviveClientRecreation:
    """Verify tokens persist in DB across fresh EtsyClient instances."""

    def test_tokens_survive_client_recreation(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Connect
            auth_resp = client.get("/api/v1/etsy/auth-url")
            state = auth_resp.json()["state"]

            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "valid_code", "state": state},
                )

            # Status check creates a fresh client each time (stateless)
            # If tokens are in DB, it should still show connected
            status = client.get("/api/v1/etsy/status").json()
            assert status["connected"] is True
            assert status["shop_id"] == 67890


class TestStateRaceCondition:
    """Verify two concurrent OAuth flows don't interfere with each other."""

    def test_two_concurrent_auth_flows(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Start two OAuth flows
            resp1 = client.get("/api/v1/etsy/auth-url")
            resp2 = client.get("/api/v1/etsy/auth-url")

            state1 = resp1.json()["state"]
            state2 = resp2.json()["state"]

            # Both states should be different
            assert state1 != state2

            # Both states should be in pending states
            assert state1 in etsy_routes_module._pending_states
            assert state2 in etsy_routes_module._pending_states

            # Complete flow 2 first
            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                resp2_cb = client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "code2", "state": state2},
                )
            assert "success: true" in resp2_cb.text

            # State 2 should be consumed, state 1 should still be valid
            assert state2 not in etsy_routes_module._pending_states
            assert state1 in etsy_routes_module._pending_states

            # Complete flow 1
            with patch.object(EtsyClient, "exchange_code", _mock_exchange_code()), \
                 patch.object(EtsyClient, "get_me", _mock_get_me()):
                resp1_cb = client.get(
                    "/api/v1/etsy/callback",
                    params={"code": "code1", "state": state1},
                )
            assert "success: true" in resp1_cb.text

    def test_expired_state_cleanup(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Add an old expired state manually
            etsy_routes_module._pending_states["old_state"] = (
                time.time() - 700,  # 11+ minutes ago
                "old_verifier",
            )

            # New auth-url request should clean up expired states
            client.get("/api/v1/etsy/auth-url")

            assert "old_state" not in etsy_routes_module._pending_states

    def test_expired_state_rejected_at_callback(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # Manually add a state that's about to expire
            old_state = "expiring_state"
            etsy_routes_module._pending_states[old_state] = (
                time.time() - 650,  # 10+ minutes ago
                "verifier",
            )

            response = client.get(
                "/api/v1/etsy/callback",
                params={"code": "code", "state": old_state},
            )
            assert "success: false" in response.text
            assert "expired" in response.text.lower()
