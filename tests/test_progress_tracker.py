"""
Unit tests for Progress Tracking Service
Tests real-time updates, subscriptions, and SSE formatting.
Target: 90%+ code coverage
"""

import pytest
import asyncio
from datetime import datetime

from coloring_book.services.progress_tracker import (
    ProgressTracker,
    ProgressUpdate,
    ProgressFormatter,
)


class TestProgressUpdate:
    """Tests for ProgressUpdate data class"""

    def test_progress_update_creation(self):
        """Should create progress update with defaults"""
        update = ProgressUpdate(
            job_id="job_001",
            processed=5,
            total=10,
            message="Processing..."
        )

        assert update.job_id == "job_001"
        assert update.processed == 5
        assert update.total == 10
        assert update.status == "processing"
        assert update.timestamp is not None

    def test_progress_update_to_dict(self):
        """Should convert to dictionary for JSON"""
        update = ProgressUpdate(
            job_id="job_001",
            processed=5,
            total=10,
            total_size=1024
        )

        data = update.to_dict()

        assert data["job_id"] == "job_001"
        assert data["processed"] == 5
        assert "timestamp" in data


class TestProgressTracker:
    """Tests for progress tracking and subscriptions"""

    @pytest.fixture
    def tracker(self):
        """Create fresh tracker for each test"""
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_subscribe_to_job(self, tracker):
        """Should create subscription queue for job"""
        queue = await tracker.subscribe("job_001")

        assert queue is not None
        assert tracker.subscriber_count("job_001") == 1

    @pytest.mark.asyncio
    async def test_publish_progress_to_subscribers(self, tracker):
        """Should publish update to all subscribers"""
        queue1 = await tracker.subscribe("job_001")
        queue2 = await tracker.subscribe("job_001")

        update = ProgressUpdate(
            job_id="job_001",
            processed=5,
            total=10,
            message="Halfway"
        )

        count = await tracker.publish_progress(update)

        assert count == 2

        received1 = await queue1.get()
        received2 = await queue2.get()

        assert received1.job_id == "job_001"
        assert received2.job_id == "job_001"

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, tracker):
        """Should remove subscription when unsubscribed"""
        queue = await tracker.subscribe("job_001")

        assert tracker.subscriber_count("job_001") == 1

        success = await tracker.unsubscribe("job_001", queue)

        assert success is True
        assert tracker.subscriber_count("job_001") == 0

    @pytest.mark.asyncio
    async def test_get_latest_progress(self, tracker):
        """Should return latest progress without subscribing"""
        update = ProgressUpdate(
            job_id="job_001",
            processed=7,
            total=10
        )

        await tracker.publish_progress(update)

        latest = tracker.get_latest_progress("job_001")

        assert latest is not None
        assert latest.processed == 7

    def test_get_all_progress(self, tracker):
        """Should return all tracked progress"""
        tracker.job_progress["job_001"] = ProgressUpdate(job_id="job_001", processed=1, total=10)
        tracker.job_progress["job_002"] = ProgressUpdate(job_id="job_002", processed=5, total=20)

        all_progress = tracker.get_all_progress()

        assert len(all_progress) == 2
        assert "job_001" in all_progress
        assert "job_002" in all_progress

    def test_clear_job_progress(self, tracker):
        """Should remove job progress"""
        tracker.job_progress["job_001"] = ProgressUpdate(job_id="job_001", processed=1, total=10)

        assert tracker.get_latest_progress("job_001") is not None

        success = tracker.clear_job_progress("job_001")

        assert success is True
        assert tracker.get_latest_progress("job_001") is None


class TestProgressFormatter:
    """Tests for progress update formatting"""

    def test_format_sse_event(self):
        """Should format update as Server-Sent Event"""
        update = ProgressUpdate(
            job_id="job_001",
            processed=5,
            total=10,
            status="processing"
        )

        sse = ProgressFormatter.format_sse(update)

        assert "event: processing" in sse
        assert "data:" in sse

    def test_format_percentage(self):
        """Should format progress as percentage"""
        update = ProgressUpdate(job_id="job_001", processed=5, total=10)

        percent = ProgressFormatter.format_percentage(update)

        assert percent == "50%"

    def test_format_percentage_complete(self):
        """Should format 100% correctly"""
        update = ProgressUpdate(job_id="job_001", processed=10, total=10)

        percent = ProgressFormatter.format_percentage(update)

        assert percent == "100%"

    def test_format_human_readable(self):
        """Should format as human-readable string"""
        update = ProgressUpdate(
            job_id="job_001",
            processed=5,
            total=10,
            message="Processing images"
        )

        readable = ProgressFormatter.format_human_readable(update)

        assert "[5/10]" in readable
        assert "50%" in readable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
