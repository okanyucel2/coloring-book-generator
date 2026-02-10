"""Tests for Etsy API routes."""

import os
from unittest.mock import patch

import coloring_book.api.etsy_routes as etsy_routes_module
import pytest
from coloring_book.api import models
from coloring_book.api import workbook_routes as wr_module
from coloring_book.api.app import app
from coloring_book.api.workbook_routes import _generation_tasks, _pdfs
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
    from coloring_book.api.app import DEFAULT_USER_ID
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


def _create_test_workbook(client):
    """Create a workbook and return its ID."""
    resp = client.post("/api/v1/workbooks", json={
        "theme": "vehicles",
        "title": "Test Workbook",
        "items": ["fire_truck", "police_car"],
        "activity_mix": {"trace_and_color": 2},
    })
    return resp.json()["id"]


class TestEtsyStatus:
    def test_status_not_connected(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "test_key", "ETSY_API_SECRET": "test_secret"}):
            # Ensure no leftover tokens from other test runs
            client.post("/api/v1/etsy/disconnect")
            response = client.get("/api/v1/etsy/status")
            assert response.status_code == 200
            assert response.json()["connected"] is False

    def test_disconnect(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "test_key", "ETSY_API_SECRET": "test_secret"}):
            response = client.post("/api/v1/etsy/disconnect")
            assert response.status_code == 200


class TestEtsyAuthURL:
    def test_get_auth_url(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "test_key_123", "ETSY_API_SECRET": "test_secret"}):
            response = client.get("/api/v1/etsy/auth-url")
            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "state" in data
            assert "test_key_123" in data["auth_url"]

    def test_get_auth_url_no_api_key(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "", "ETSY_API_SECRET": ""}, clear=False):
            response = client.get("/api/v1/etsy/auth-url")
            assert response.status_code == 503

    def test_callback_invalid_state(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            # First get auth URL to set state
            client.get("/api/v1/etsy/auth-url")

            # Try callback with wrong state — returns HTML error page
            response = client.get(
                "/api/v1/etsy/callback",
                params={"code": "test_code", "state": "wrong_state"},
            )
            assert response.status_code == 200  # HTML response
            assert "etsy-oauth-complete" in response.text
            assert "success: false" in response.text


class TestListingPreview:
    def test_preview_listing(self, client):
        wb_id = _create_test_workbook(client)
        response = client.get(f"/api/v1/etsy/workbooks/{wb_id}/listing-preview")
        assert response.status_code == 200
        data = response.json()
        assert "Vehicles" in data["title"]
        assert data["price"] > 0
        assert len(data["tags"]) <= 13
        assert len(data["description"]) > 50

    def test_preview_not_found(self, client):
        response = client.get("/api/v1/etsy/workbooks/nonexistent/listing-preview")
        assert response.status_code == 404


class TestPublishWorkbook:
    def test_publish_not_authenticated(self, client, db_session):
        wb_id = _create_test_workbook(client)

        # Set workbook status to ready via DB
        session = db_session()
        wb = session.query(models.WorkbookModel).filter(
            models.WorkbookModel.id == wb_id
        ).first()
        wb.status = "ready"
        session.commit()
        session.close()

        _pdfs[wb_id] = b"%PDF-1.4 test"

        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            response = client.post(f"/api/v1/etsy/workbooks/{wb_id}/publish", json={
                "shop_id": 12345,
            })
            assert response.status_code == 401

    def test_publish_not_ready(self, client):
        wb_id = _create_test_workbook(client)

        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            response = client.post(f"/api/v1/etsy/workbooks/{wb_id}/publish", json={
                "shop_id": 12345,
            })
            assert response.status_code == 409

    def test_publish_not_found(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            response = client.post("/api/v1/etsy/workbooks/nonexistent/publish", json={
                "shop_id": 12345,
            })
            assert response.status_code == 404
