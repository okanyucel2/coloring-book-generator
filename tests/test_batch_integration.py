"""Tests for batch generation integration: router, worker, schemas."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from coloring_book.api.batch_schemas import (
    BatchItemInput,
    BatchOptions,
    BatchSubmitRequest,
    BatchSubmitResponse,
)
from coloring_book.services.batch_queue_optimized import (
    BatchItem,
    BatchJob,
    BatchQueue,
    JobStatus,
    QueueFullError,
)
from coloring_book.services.progress_tracker_optimized import (
    ProgressTracker,
    ProgressUpdate,
)
from coloring_book.services.zip_export import ZipExportService


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestBatchSchemas:
    """Validate Pydantic schema models."""

    def test_batch_item_input(self):
        item = BatchItemInput(file="cat.png", prompt="a cute cat")
        assert item.file == "cat.png"
        assert item.prompt == "a cute cat"

    def test_batch_options_defaults(self):
        opts = BatchOptions()
        assert opts.quality == "standard"
        assert opts.include_pdf is False

    def test_batch_submit_request_minimal(self):
        req = BatchSubmitRequest(
            items=[BatchItemInput(file="a.png", prompt="test")]
        )
        assert req.model == "claude"
        assert len(req.items) == 1
        assert req.options.quality == "standard"

    def test_batch_submit_request_full(self):
        req = BatchSubmitRequest(
            items=[
                BatchItemInput(file="a.png", prompt="cat"),
                BatchItemInput(file="b.png", prompt="dog"),
            ],
            model="gemini",
            options=BatchOptions(quality="high", include_pdf=True),
        )
        assert req.model == "gemini"
        assert len(req.items) == 2
        assert req.options.include_pdf is True

    def test_batch_submit_request_empty_items_fails(self):
        with pytest.raises(Exception):
            BatchSubmitRequest(items=[])

    def test_batch_submit_response(self):
        resp = BatchSubmitResponse(
            batch_id="batch_abc123",
            status="pending",
            total_items=3,
        )
        assert resp.batch_id == "batch_abc123"
        assert resp.total_items == 3


# ---------------------------------------------------------------------------
# BatchQueue integration tests
# ---------------------------------------------------------------------------

class TestBatchQueueIntegration:
    """Test optimized BatchQueue with real asyncio."""

    async def test_add_and_get_job(self):
        queue = BatchQueue(max_queue_size=10)
        job = BatchJob(
            id="test_job_1",
            items=[BatchItem(id="item_1", file="cat.png", prompt="cat")],
            model="claude",
            options={},
        )
        job_id = await queue.add_job(job)
        assert job_id == "test_job_1"
        assert queue.queue_size() == 1

        retrieved = await queue.get_job()
        assert retrieved is not None
        assert retrieved.id == "test_job_1"
        assert queue.queue_size() == 0

    async def test_get_job_empty_queue(self):
        queue = BatchQueue()
        result = await queue.get_job()
        assert result is None

    async def test_job_status_tracking(self):
        queue = BatchQueue()
        job = BatchJob(
            id="job_status",
            items=[
                BatchItem(id="i1", file="a.png", prompt="a"),
                BatchItem(id="i2", file="b.png", prompt="b"),
            ],
            model="claude",
            options={},
        )
        await queue.add_job(job)

        # Check initial progress
        progress = queue.get_job_progress("job_status")
        assert progress is not None
        assert progress["total_items"] == 2
        assert progress["processed"] == 0
        assert progress["progress_percent"] == 0

        # Update item status
        queue.update_item_status("job_status", "i1", JobStatus.COMPLETED, output_path="/tmp/a.png")
        progress = queue.get_job_progress("job_status")
        assert progress["processed"] == 1
        assert progress["progress_percent"] == 50

    async def test_cancel_job(self):
        queue = BatchQueue()
        job = BatchJob(
            id="job_cancel",
            items=[BatchItem(id="i1", file="a.png", prompt="a")],
            model="claude",
            options={},
        )
        await queue.add_job(job)

        success = queue.update_job_status("job_cancel", JobStatus.CANCELLED)
        assert success is True

        status = queue.get_job_status("job_cancel")
        assert status.status == JobStatus.CANCELLED

    async def test_list_jobs(self):
        queue = BatchQueue()
        for i in range(3):
            job = BatchJob(
                id=f"job_{i}",
                items=[BatchItem(id=f"item_{i}", file=f"{i}.png", prompt="x")],
                model="claude",
                options={},
            )
            await queue.add_job(job)

        jobs = queue.list_jobs(limit=10)
        assert len(jobs) == 3

    async def test_nonexistent_job_returns_none(self):
        queue = BatchQueue()
        assert queue.get_job_status("nonexistent") is None
        assert queue.get_job_progress("nonexistent") is None


# ---------------------------------------------------------------------------
# ProgressTracker tests
# ---------------------------------------------------------------------------

class TestProgressTracker:
    """Test progress tracker subscribe/publish/unsubscribe."""

    async def test_subscribe_and_receive(self):
        tracker = ProgressTracker()
        sub_queue = await tracker.subscribe("job_1")

        update = ProgressUpdate(
            job_id="job_1", processed=1, total=5, message="item 1 done"
        )
        count = await tracker.publish_progress(update)
        assert count == 1

        received = await asyncio.wait_for(sub_queue.get(), timeout=1.0)
        assert received.processed == 1
        assert received.message == "item 1 done"

    async def test_multiple_subscribers(self):
        tracker = ProgressTracker()
        q1 = await tracker.subscribe("job_multi")
        q2 = await tracker.subscribe("job_multi")

        update = ProgressUpdate(
            job_id="job_multi", processed=3, total=10, message="progress"
        )
        count = await tracker.publish_progress(update)
        assert count == 2

        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert r1.processed == 3
        assert r2.processed == 3

    async def test_unsubscribe(self):
        tracker = ProgressTracker()
        q = await tracker.subscribe("job_unsub")
        result = await tracker.unsubscribe("job_unsub", q)
        assert result is True
        assert tracker.subscriber_count("job_unsub") == 0

    async def test_close_all_subscriptions(self):
        tracker = ProgressTracker()
        q1 = await tracker.subscribe("job_close")
        q2 = await tracker.subscribe("job_close")

        await tracker.close_all_subscriptions("job_close")

        # Should receive None (end-of-stream)
        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        assert r1 is None

    async def test_latest_progress(self):
        tracker = ProgressTracker()
        assert tracker.get_latest_progress("no_job") is None

        update = ProgressUpdate(job_id="job_latest", processed=5, total=10)
        await tracker.publish_progress(update)

        latest = tracker.get_latest_progress("job_latest")
        assert latest is not None
        assert latest.processed == 5


# ---------------------------------------------------------------------------
# Batch Router API tests (using httpx AsyncClient)
# ---------------------------------------------------------------------------

class TestBatchRouterAPI:
    """Test batch API endpoints via TestClient."""

    @pytest.fixture
    async def client(self):
        """Create test client with batch services injected."""
        from coloring_book.api import batch_router as batch_router_module
        from coloring_book.api.batch_router import router

        # Create real service instances for testing
        queue = BatchQueue(max_queue_size=50)
        await queue.start()
        tracker = ProgressTracker()
        zip_svc = ZipExportService(temp_dir=tempfile.mkdtemp())

        # Inject into router module
        batch_router_module.batch_queue = queue
        batch_router_module.progress_tracker = tracker
        batch_router_module.zip_service = zip_svc

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        await queue.stop()
        await tracker.shutdown()

        # Reset module globals
        batch_router_module.batch_queue = None
        batch_router_module.progress_tracker = None
        batch_router_module.zip_service = None

    async def test_submit_batch(self, client):
        resp = await client.post("/api/v1/batch/generate", json={
            "items": [
                {"file": "cat.png", "prompt": "a cute cat"},
                {"file": "dog.png", "prompt": "a playful dog"},
            ],
            "model": "claude",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "batch_id" in data
        assert data["status"] == "pending"
        assert data["total_items"] == 2

    async def test_submit_empty_batch_fails(self, client):
        resp = await client.post("/api/v1/batch/generate", json={
            "items": [],
        })
        assert resp.status_code == 422  # Pydantic validation error

    async def test_list_batches_empty(self, client):
        resp = await client.get("/api/v1/batch")
        assert resp.status_code == 200
        data = resp.json()
        assert data["batches"] == []
        assert data["count"] == 0

    async def test_list_batches_after_submit(self, client):
        await client.post("/api/v1/batch/generate", json={
            "items": [{"file": "a.png", "prompt": "test"}],
        })
        resp = await client.get("/api/v1/batch")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    async def test_batch_status_poll(self, client):
        submit = await client.post("/api/v1/batch/generate", json={
            "items": [{"file": "a.png", "prompt": "test"}],
        })
        batch_id = submit.json()["batch_id"]

        resp = await client.get(f"/api/v1/batch/{batch_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == batch_id
        assert data["total_items"] == 1

    async def test_batch_status_not_found(self, client):
        resp = await client.get("/api/v1/batch/nonexistent/status")
        assert resp.status_code == 404

    async def test_cancel_batch(self, client):
        submit = await client.post("/api/v1/batch/generate", json={
            "items": [{"file": "a.png", "prompt": "test"}],
        })
        batch_id = submit.json()["batch_id"]

        resp = await client.post(f"/api/v1/batch/{batch_id}/cancel")
        assert resp.status_code == 200
        assert "cancelled" in resp.json()["message"]

    async def test_cancel_nonexistent_batch(self, client):
        resp = await client.post("/api/v1/batch/nonexistent/cancel")
        assert resp.status_code == 404

    async def test_download_not_completed(self, client):
        submit = await client.post("/api/v1/batch/generate", json={
            "items": [{"file": "a.png", "prompt": "test"}],
        })
        batch_id = submit.json()["batch_id"]

        resp = await client.get(f"/api/v1/batch/{batch_id}/download")
        assert resp.status_code == 400  # Not ready

    async def test_download_not_found(self, client):
        resp = await client.get("/api/v1/batch/nonexistent/download")
        assert resp.status_code == 404

    async def test_invalid_status_filter(self, client):
        resp = await client.get("/api/v1/batch?status=invalid_status")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Batch Worker tests
# ---------------------------------------------------------------------------

class TestBatchWorker:
    """Test batch worker processing logic."""

    async def test_worker_processes_job(self):
        """Worker should pick up a job, process items, and publish progress."""
        from coloring_book.services.batch_worker import _process_job

        queue = BatchQueue()
        tracker = ProgressTracker()
        zip_svc = ZipExportService(temp_dir=tempfile.mkdtemp())

        job = BatchJob(
            id="worker_test",
            items=[BatchItem(id="wi1", file="test_cat.png", prompt="cat")],
            model="claude",
            options={},
        )
        await queue.add_job(job)

        # Subscribe to track progress events
        sub = await tracker.subscribe("worker_test")

        # Mock the image generation to avoid real AI calls
        with patch(
            "coloring_book.services.batch_worker._generate_item"
        ) as mock_gen:
            # Create a temp file to simulate output
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(b"fake png data")
            tmp.close()
            mock_gen.return_value = tmp.name

            await _process_job(job, queue, tracker, zip_svc)

            # Verify progress was published
            events = []
            while not sub.empty():
                events.append(await sub.get())

            assert len(events) >= 2  # At least: start + completed
            assert events[-1].status in ("completed", "failed")

            # Cleanup
            os.unlink(tmp.name)

        await tracker.shutdown()

    async def test_worker_handles_generation_error(self):
        """Worker should handle item generation failures gracefully."""
        from coloring_book.services.batch_worker import _process_job

        queue = BatchQueue()
        tracker = ProgressTracker()
        zip_svc = ZipExportService(temp_dir=tempfile.mkdtemp())

        job = BatchJob(
            id="worker_err",
            items=[BatchItem(id="ei1", file="bad.png", prompt="error")],
            model="claude",
            options={},
        )
        await queue.add_job(job)

        with patch(
            "coloring_book.services.batch_worker._generate_item",
            side_effect=RuntimeError("generation failed"),
        ):
            await _process_job(job, queue, tracker, zip_svc)

        # Job should be marked as failed
        progress = queue.get_job_progress("worker_err")
        assert progress["failed"] == 1

        await tracker.shutdown()


# ---------------------------------------------------------------------------
# ZipExportService tests
# ---------------------------------------------------------------------------

class TestZipExportService:
    """Test ZIP creation and streaming."""

    def test_create_zip(self, tmp_path):
        svc = ZipExportService(temp_dir=str(tmp_path / "zip_tmp"))

        # Create test files
        f1 = tmp_path / "image1.png"
        f1.write_bytes(b"fake png 1")
        f2 = tmp_path / "image2.png"
        f2.write_bytes(b"fake png 2")

        result = svc.create_zip(
            str(tmp_path / "output.zip"),
            [
                {"path": str(f1), "arcname": "image1.png"},
                {"path": str(f2), "arcname": "image2.png"},
            ],
        )
        assert result["status"] == "success"
        assert result["file_count"] == 2
        assert os.path.exists(result["zip_path"])

    def test_stream_zip(self, tmp_path):
        svc = ZipExportService(temp_dir=str(tmp_path / "zip_tmp"))

        f1 = tmp_path / "img.png"
        f1.write_bytes(b"test data")

        buf = svc.stream_zip([{"path": str(f1), "arcname": "img.png"}])
        assert buf is not None
        assert buf.readable()
        content = buf.read()
        assert len(content) > 0

    def test_create_zip_file_not_found(self, tmp_path):
        svc = ZipExportService(temp_dir=str(tmp_path / "zip_tmp"))
        result = svc.create_zip(
            str(tmp_path / "fail.zip"),
            [{"path": "/nonexistent/file.png", "arcname": "file.png"}],
        )
        assert result["status"] == "error"
        assert result["error_type"] == "file_not_found"

    def test_validate_zip(self, tmp_path):
        svc = ZipExportService(temp_dir=str(tmp_path / "zip_tmp"))

        f1 = tmp_path / "v.png"
        f1.write_bytes(b"data")

        zip_path = str(tmp_path / "valid.zip")
        svc.create_zip(zip_path, [{"path": str(f1), "arcname": "v.png"}])

        result = svc.validate_zip(zip_path)
        assert result["valid"] is True
        assert result["file_count"] == 1
