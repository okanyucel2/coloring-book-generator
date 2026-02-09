"""Tests for workbook API endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from coloring_book.api.app import app
from coloring_book.api.workbook_routes import _pdfs, _workbooks, _generation_tasks


@pytest.fixture(autouse=True)
def cleanup_workbooks():
    """Clear in-memory workbook stores between tests."""
    _workbooks.clear()
    _pdfs.clear()
    _generation_tasks.clear()
    yield
    _workbooks.clear()
    _pdfs.clear()
    _generation_tasks.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _create_workbook(client, **overrides):
    """Helper: create a workbook via API and return response JSON."""
    body = {
        "theme": "vehicles",
        "title": "Test Vehicles Workbook",
        "subtitle": "For Boys Ages 3-5",
        "age_min": 3,
        "age_max": 5,
        "page_count": 10,
        "items": ["fire_truck", "police_car", "ambulance"],
        "activity_mix": {
            "trace_and_color": 3,
            "which_different": 1,
            "count_circle": 1,
            "match": 1,
            "word_to_image": 1,
            "find_circle": 1,
        },
        "page_size": "letter",
    }
    body.update(overrides)
    response = client.post("/api/v1/workbooks", json=body)
    return response


class TestThemeEndpoints:
    def test_list_themes(self, client):
        response = client.get("/api/v1/themes")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 2
        slugs = [t["slug"] for t in data]
        assert "vehicles" in slugs
        assert "animals" in slugs

    def test_theme_detail(self, client):
        response = client.get("/api/v1/themes/vehicles")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "vehicles"
        assert data["display_name"] == "Vehicles"
        assert len(data["items"]) >= 18
        assert data["item_count"] == len(data["items"])

    def test_theme_detail_animals(self, client):
        response = client.get("/api/v1/themes/animals")
        assert response.status_code == 200
        assert response.json()["category"] == "animal"

    def test_theme_not_found(self, client):
        response = client.get("/api/v1/themes/nonexistent")
        assert response.status_code == 404

    def test_theme_has_etsy_tags(self, client):
        response = client.get("/api/v1/themes/vehicles")
        tags = response.json()["etsy_tags"]
        assert len(tags) > 0
        assert len(tags) <= 13


class TestWorkbookCRUD:
    def test_create_workbook(self, client):
        response = _create_workbook(client)
        assert response.status_code == 201
        data = response.json()
        assert data["theme"] == "vehicles"
        assert data["title"] == "Test Vehicles Workbook"
        assert data["status"] == "draft"
        assert data["id"] is not None

    def test_create_workbook_minimal(self, client):
        response = client.post("/api/v1/workbooks", json={
            "theme": "vehicles",
            "title": "Quick Test",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["items"] == [
            "traffic_light", "police_car", "ambulance", "school_bus",
            "crane", "dump_truck", "excavator", "cement_mixer",
            "fire_truck", "garbage_truck", "helicopter", "airplane",
            "tractor", "train", "tow_truck", "bulldozer", "taxi", "bicycle",
        ]

    def test_create_workbook_invalid_theme(self, client):
        response = _create_workbook(client, theme="dinosaurs")
        assert response.status_code == 400
        assert "Unknown theme" in response.json()["detail"]

    def test_create_workbook_invalid_age_range(self, client):
        response = _create_workbook(client, age_min=8, age_max=3)
        assert response.status_code == 400

    def test_list_workbooks_empty(self, client):
        response = client.get("/api/v1/workbooks")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_workbooks_with_data(self, client):
        _create_workbook(client)
        _create_workbook(client, title="Second Workbook")
        response = client.get("/api/v1/workbooks")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_workbook(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/workbooks/{wb_id}")
        assert response.status_code == 200
        assert response.json()["id"] == wb_id

    def test_get_workbook_not_found(self, client):
        response = client.get("/api/v1/workbooks/nonexistent")
        assert response.status_code == 404

    def test_update_workbook(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.put(f"/api/v1/workbooks/{wb_id}", json={
            "title": "Updated Title",
            "page_count": 20,
        })
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["page_count"] == 20

    def test_update_workbook_not_found(self, client):
        response = client.put("/api/v1/workbooks/nonexistent", json={
            "title": "Test",
        })
        assert response.status_code == 404

    def test_delete_workbook(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/workbooks/{wb_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/api/v1/workbooks/{wb_id}")
        assert response.status_code == 404

    def test_delete_workbook_not_found(self, client):
        response = client.delete("/api/v1/workbooks/nonexistent")
        assert response.status_code == 404


class TestWorkbookGeneration:
    def test_generate_workbook(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/workbooks/{wb_id}/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"
        assert data["progress"] == 0.0

    def test_generate_not_found(self, client):
        response = client.post("/api/v1/workbooks/nonexistent/generate")
        assert response.status_code == 404

    def test_status_endpoint(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/workbooks/{wb_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_status_not_found(self, client):
        response = client.get("/api/v1/workbooks/nonexistent/status")
        assert response.status_code == 404

    def test_download_not_ready(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/workbooks/{wb_id}/download")
        assert response.status_code == 409

    def test_download_not_found(self, client):
        response = client.get("/api/v1/workbooks/nonexistent/download")
        assert response.status_code == 404

    def test_preview_endpoint(self, client):
        create_resp = _create_workbook(client)
        wb_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/workbooks/{wb_id}/preview")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Vehicles Workbook"
        assert data["total_pages"] > 0

    def test_preview_not_found(self, client):
        response = client.get("/api/v1/workbooks/nonexistent/preview")
        assert response.status_code == 404

    def test_full_generation_cycle(self, client):
        """End-to-end: create → generate → wait → download."""
        # Create
        create_resp = _create_workbook(client, items=["fire_truck", "police_car"],
                                        activity_mix={"trace_and_color": 2})
        wb_id = create_resp.json()["id"]

        # Generate
        gen_resp = client.post(f"/api/v1/workbooks/{wb_id}/generate")
        assert gen_resp.status_code == 200

        # Wait for async generation to complete
        import time
        for _ in range(50):  # max 5 seconds
            status = client.get(f"/api/v1/workbooks/{wb_id}/status").json()
            if status["status"] in ("ready", "failed"):
                break
            time.sleep(0.1)

        # Verify ready
        final_status = client.get(f"/api/v1/workbooks/{wb_id}/status").json()
        assert final_status["status"] == "ready"
        assert final_status["progress"] == 1.0

        # Download
        download_resp = client.get(f"/api/v1/workbooks/{wb_id}/download")
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"] == "application/pdf"
        assert download_resp.content[:5] == b"%PDF-"


class TestWorkbookSchemaValidation:
    def test_page_size_validation(self, client):
        response = _create_workbook(client, page_size="b5")
        assert response.status_code == 422

    def test_age_min_negative(self, client):
        response = _create_workbook(client, age_min=-1)
        assert response.status_code == 422

    def test_page_count_too_low(self, client):
        response = _create_workbook(client, page_count=2)
        assert response.status_code == 422

    def test_page_count_too_high(self, client):
        response = _create_workbook(client, page_count=200)
        assert response.status_code == 422

    def test_empty_title(self, client):
        response = _create_workbook(client, title="")
        assert response.status_code == 422

    def test_a4_page_size_accepted(self, client):
        response = _create_workbook(client, page_size="a4")
        assert response.status_code == 201
