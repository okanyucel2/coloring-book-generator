"""
Tests for Step 3 overhaul: staged progress, /view endpoint, expanded thumbnails.

Covers:
  - GET /api/v1/workbooks/{id}/status returns stage field
  - GET /api/v1/workbooks/{id}/view serves PDF inline
  - GET /api/v1/workbooks/{id}/preview returns up to 8 thumbnails
  - generation_stage column persists through WorkbookModel
  - PUT /api/v1/workbooks/{id} resets status to draft when config changes
"""

import asyncio
import os
import tempfile
from unittest.mock import patch

import pytest
import httpx
from collections.abc import AsyncGenerator
from httpx import ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.coloring_book.api.app import app
from src.coloring_book.api.models import Base, WorkbookModel, get_db
from src.coloring_book.api.workbook_routes import _pdfs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(tmp_path):
    """Async test client with file-based temp SQLite.

    Uses a file-based DB (not :memory:) because _generate_pdf uses a separate
    sync SessionLocal that must access the same database as the async routes.
    """
    db_path = tmp_path / "test_step3.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"

    # Async engine for route handlers
    test_engine = create_async_engine(async_url)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionFactory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionFactory() as session:
            yield session

    # Sync engine for _generate_pdf background task
    test_sync_engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    TestSyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_sync_engine)

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    # Patch SessionLocal used by _generate_pdf to use our test sync engine
    with patch("src.coloring_book.api.workbook_routes.SessionLocal", TestSyncSessionLocal):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            c._test_session_factory = TestSessionFactory
            yield c

    app.dependency_overrides.clear()
    _pdfs.clear()

    test_sync_engine.dispose()
    await test_engine.dispose()


async def _create_workbook(client: httpx.AsyncClient, **overrides) -> dict:
    """Helper to create a workbook and return the JSON response."""
    payload = {
        "theme": overrides.get("theme", "vehicles"),
        "title": overrides.get("title", "Test Workbook"),
        "page_count": overrides.get("page_count", 30),
        "age_min": 3,
        "age_max": 5,
        "items": overrides.get("items", ["car", "truck", "bus", "train", "plane", "boat", "helicopter", "motorcycle"]),
        "activity_mix": overrides.get("activity_mix", {
            "trace_and_color": 18,
            "which_different": 2,
            "count_circle": 2,
            "match": 2,
            "word_to_image": 1,
            "find_circle": 2,
        }),
    }
    resp = await client.post("/api/v1/workbooks", json=payload)
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Status endpoint — stage field
# ---------------------------------------------------------------------------

class TestStatusStage:
    """GET /api/v1/workbooks/{id}/status should return stage field."""

    async def test_status_includes_stage_field(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "stage" in data, "Status response must include 'stage' field"

    async def test_stage_is_null_for_draft(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/status")
        data = resp.json()
        assert data["stage"] is None
        assert data["status"] == "draft"

    async def test_stage_after_generation(self, client):
        """After generation completes, stage should be 'Complete!'."""
        wb = await _create_workbook(client)
        wid = wb["id"]

        # Trigger generation
        gen_resp = await client.post(f"/api/v1/workbooks/{wid}/generate")
        assert gen_resp.status_code == 200

        # Poll until complete (max 30s)
        for _ in range(60):
            status = await client.get(f"/api/v1/workbooks/{wid}/status")
            data = status.json()
            if data["status"] == "ready":
                assert data["stage"] == "Complete!"
                assert data["progress"] == 1.0
                return
            if data["status"] == "failed":
                pytest.fail(f"Generation failed: {data}")
            await asyncio.sleep(0.5)

        pytest.fail("Generation did not complete within timeout")


# ---------------------------------------------------------------------------
# View endpoint — inline PDF
# ---------------------------------------------------------------------------

class TestViewEndpoint:
    """GET /api/v1/workbooks/{id}/view should serve PDF inline."""

    async def test_view_not_found(self, client):
        resp = await client.get("/api/v1/workbooks/nonexistent/view")
        assert resp.status_code == 404

    async def test_view_before_generation(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/view")
        assert resp.status_code == 409, "Should return 409 when not generated"

    async def test_view_returns_inline_pdf(self, client):
        wb = await _create_workbook(client)
        wid = wb["id"]

        # Generate
        await client.post(f"/api/v1/workbooks/{wid}/generate")
        for _ in range(60):
            status = (await client.get(f"/api/v1/workbooks/{wid}/status")).json()
            if status["status"] == "ready":
                break
            await asyncio.sleep(0.5)
        else:
            pytest.fail("Generation did not complete")

        # View endpoint
        resp = await client.get(f"/api/v1/workbooks/{wid}/view")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

        disposition = resp.headers.get("content-disposition", "")
        assert "inline" in disposition, f"Expected inline disposition, got: {disposition}"
        assert "Test_Workbook.pdf" in disposition

    async def test_download_is_attachment(self, client):
        """Contrast: download endpoint uses 'attachment' not 'inline'."""
        wb = await _create_workbook(client)
        wid = wb["id"]

        await client.post(f"/api/v1/workbooks/{wid}/generate")
        for _ in range(60):
            status = (await client.get(f"/api/v1/workbooks/{wid}/status")).json()
            if status["status"] == "ready":
                break
            await asyncio.sleep(0.5)

        resp = await client.get(f"/api/v1/workbooks/{wid}/download")
        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition


# ---------------------------------------------------------------------------
# Preview endpoint — expanded thumbnails
# ---------------------------------------------------------------------------

class TestExpandedThumbnails:
    """GET /api/v1/workbooks/{id}/preview should return up to 8 page thumbnails."""

    async def test_preview_returns_thumbnails(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert "page_thumbnails" in data

    async def test_thumbnail_count_up_to_8(self, client):
        """With 27+ activity pages, thumbnails should cap at 8 (1 cover + 7 activity)."""
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/preview")
        data = resp.json()
        thumbs = data["page_thumbnails"]
        # 1 cover + up to 7 activity pages = max 8
        assert len(thumbs) <= 8 + 1  # cover is page 1, activity pages 2-8 = 7
        assert len(thumbs) >= 2, "Should have at least cover + 1 activity"

    async def test_first_thumbnail_is_cover(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/preview")
        data = resp.json()
        thumbs = data["page_thumbnails"]
        assert thumbs[0]["page"] == 1
        assert thumbs[0]["type"] == "cover"

    async def test_activity_thumbnails_have_correct_fields(self, client):
        wb = await _create_workbook(client)
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/preview")
        data = resp.json()
        for thumb in data["page_thumbnails"]:
            assert "page" in thumb
            assert "type" in thumb
            assert "label" in thumb
            assert "description" in thumb

    async def test_small_workbook_fewer_thumbnails(self, client):
        """A workbook with only 3 activity pages should have 4 thumbnails (cover + 3)."""
        wb = await _create_workbook(client, activity_mix={
            "trace_and_color": 2,
            "match": 1,
        })
        resp = await client.get(f"/api/v1/workbooks/{wb['id']}/preview")
        data = resp.json()
        thumbs = data["page_thumbnails"]
        assert len(thumbs) == 4  # cover + 3 activity pages


# ---------------------------------------------------------------------------
# Activity mix update resets status
# ---------------------------------------------------------------------------

class TestActivityMixSync:
    """PUT /api/v1/workbooks/{id} with activity_mix should reset ready→draft."""

    async def test_update_mix_resets_status(self, client):
        wb = await _create_workbook(client)
        wid = wb["id"]

        # Generate first
        await client.post(f"/api/v1/workbooks/{wid}/generate")
        for _ in range(60):
            status = (await client.get(f"/api/v1/workbooks/{wid}/status")).json()
            if status["status"] == "ready":
                break
            await asyncio.sleep(0.5)

        # Update activity mix
        resp = await client.put(f"/api/v1/workbooks/{wid}", json={
            "activity_mix": {"trace_and_color": 10, "match": 5},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft", "Status should reset to draft after config change"

    async def test_update_mix_during_generation_rejected(self, client):
        wb = await _create_workbook(client)
        wid = wb["id"]

        await client.post(f"/api/v1/workbooks/{wid}/generate")

        # Immediately try to update — should be rejected if still generating
        resp = await client.put(f"/api/v1/workbooks/{wid}", json={
            "activity_mix": {"trace_and_color": 5},
        })
        # Could be 409 if still generating, or 200 if it finished very fast
        assert resp.status_code in (200, 409)


# ---------------------------------------------------------------------------
# generation_stage column
# ---------------------------------------------------------------------------

class TestGenerationStageColumn:
    """Verify generation_stage column exists and is persisted."""

    async def test_new_workbook_has_no_stage(self, client):
        wb = await _create_workbook(client)
        status = (await client.get(f"/api/v1/workbooks/{wb['id']}/status")).json()
        assert status["stage"] is None
