"""Tests for Etsy API routes."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from coloring_book.api.app import app
from coloring_book.api.etsy_routes import _etsy_client, _etsy_state
from coloring_book.api.workbook_routes import _pdfs, _workbooks, _generation_tasks
from coloring_book.etsy.client import EtsyClient, TokenResponse
import coloring_book.api.etsy_routes as etsy_routes_module


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up state between tests."""
    _workbooks.clear()
    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._etsy_client = None
    etsy_routes_module._etsy_state = None
    yield
    _workbooks.clear()
    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._etsy_client = None
    etsy_routes_module._etsy_state = None


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

            # Try callback with wrong state
            response = client.post("/api/v1/etsy/callback", json={
                "code": "test_code",
                "state": "wrong_state",
            })
            assert response.status_code == 400


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
    def test_publish_not_authenticated(self, client):
        wb_id = _create_test_workbook(client)
        # Mark as ready and add fake PDF
        _workbooks[wb_id]["status"] = "ready"
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
