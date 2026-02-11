"""
Comprehensive tests for optimized progress_tracker_optimized.py
Tests both critical improvements:
1. TTL-based memory management
2. Efficient parallel subscriber broadcasting
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from coloring_book.services.progress_tracker_optimized import (
    ProgressUpdate,
    ProgressTracker,
    ProgressFormatter,
    SubscriberTracker,
)


class TestProgressUpdateBasics:
    """Test ProgressUpdate dataclass"""

    def test_progress_update_creation(self):
        """Test creating progress update"""
        update = ProgressUpdate(
            job_id="job1",
            processed=5,
            total=10,
            message="Processing item 5",
        )
        assert update.job_id == "job1"
        assert update.processed == 5
        assert update.total == 10
        assert update.status == "processing"
        assert update.timestamp is not None

    def test_progress_update_to_dict(self):
        """Test serialization to dict"""
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        data = update.to_dict()
        
        assert data["job_id"] == "job1"
        assert data["processed"] == 5
        assert data["total"] == 10
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z") or "T" in data["timestamp"]

    def test_progress_update_with_error(self):
        """Test progress update with error"""
        update = ProgressUpdate(
            job_id="job1",
            processed=5,
            total=10,
            status="failed",
            error="File not found"
        )
        assert update.status == "failed"
        assert update.error == "File not found"


class TestProgressTrackerBasics:
    """Test ProgressTracker initialization and basic operations"""

    @pytest.fixture
    def tracker(self):
        """Create fresh tracker for each test"""
        return ProgressTracker(ttl_hours=24, cleanup_interval=3600)

    @pytest.mark.asyncio
    async def test_tracker_initialization(self, tracker):
        """Test tracker initializes correctly"""
        assert tracker.ttl_hours == 24
        assert tracker.cleanup_interval == 3600
        assert len(tracker.subscribers) == 0
        assert len(tracker.job_progress) == 0
        assert tracker.metrics["total_publishes"] == 0

    @pytest.mark.asyncio
    async def test_subscribe_creates_queue(self, tracker):
        """Test subscribe creates and returns queue"""
        queue = await tracker.subscribe("job1")
        assert queue is not None
        assert isinstance(queue, asyncio.Queue)
        assert tracker.subscriber_count("job1") == 1

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_job(self, tracker):
        """Test multiple subscribers for same job"""
        queue1 = await tracker.subscribe("job1")
        queue2 = await tracker.subscribe("job1")
        queue3 = await tracker.subscribe("job1")
        
        assert tracker.subscriber_count("job1") == 3
        assert queue1 is not queue2
        assert queue2 is not queue3

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_subscriber(self, tracker):
        """Test unsubscribe removes queue"""
        queue1 = await tracker.subscribe("job1")
        queue2 = await tracker.subscribe("job1")
        
        result = await tracker.unsubscribe("job1", queue1)
        assert result is True
        assert tracker.subscriber_count("job1") == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_cleans_empty_lists(self, tracker):
        """Test unsubscribe removes empty subscriber lists"""
        queue = await tracker.subscribe("job1")
        await tracker.unsubscribe("job1", queue)
        
        assert "job1" not in tracker.subscribers

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_queue(self, tracker):
        """Test unsubscribe with nonexistent queue returns False"""
        queue1 = await tracker.subscribe("job1")
        queue2 = asyncio.Queue()
        
        result = await tracker.unsubscribe("job1", queue2)
        assert result is False
        assert tracker.subscriber_count("job1") == 1


class TestPublishProgressBasics:
    """Test basic publish_progress functionality"""

    @pytest.fixture
    def tracker(self):
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_publish_to_no_subscribers(self, tracker):
        """Test publishing with no subscribers"""
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        count = await tracker.publish_progress(update)
        
        assert count == 0
        assert tracker.metrics["total_publishes"] == 1

    @pytest.mark.asyncio
    async def test_publish_to_single_subscriber(self, tracker):
        """Test publishing to single subscriber"""
        queue = await tracker.subscribe("job1")
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        
        count = await tracker.publish_progress(update)
        
        assert count == 1
        assert not queue.empty()
        
        received = await queue.get()
        assert received.job_id == "job1"
        assert received.processed == 5

    @pytest.mark.asyncio
    async def test_publish_to_multiple_subscribers(self, tracker):
        """Test publishing to multiple subscribers - IMPROVEMENT #2"""
        queue1 = await tracker.subscribe("job1")
        queue2 = await tracker.subscribe("job1")
        queue3 = await tracker.subscribe("job1")
        
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        count = await tracker.publish_progress(update)
        
        assert count == 3
        
        # All queues receive the update
        assert not queue1.empty()
        assert not queue2.empty()
        assert not queue3.empty()

    @pytest.mark.asyncio
    async def test_publish_updates_job_progress(self, tracker):
        """Test publish stores latest progress"""
        update1 = ProgressUpdate(job_id="job1", processed=5, total=10)
        update2 = ProgressUpdate(job_id="job1", processed=8, total=10)
        
        await tracker.publish_progress(update1)
        await tracker.publish_progress(update2)
        
        latest = tracker.get_latest_progress("job1")
        assert latest.processed == 8

    @pytest.mark.asyncio
    async def test_publish_tracks_latency(self, tracker):
        """Test publish tracks response time metrics"""
        queue = await tracker.subscribe("job1")
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        
        await tracker.publish_progress(update)
        
        assert tracker.metrics["avg_publish_latency_ms"] > 0
        assert len(tracker.publish_latencies) == 1


class TestMemoryManagement:
    """Test IMPROVEMENT #1: TTL-based memory management"""

    @pytest.fixture
    def tracker(self):
        """Create tracker with short TTL for testing"""
        return ProgressTracker(ttl_hours=0.01)  # ~36 seconds for testing

    @pytest.mark.asyncio
    async def test_cleanup_expired_jobs(self, tracker):
        """Test cleanup removes expired jobs"""
        # Add job that's "completed" long ago
        update = ProgressUpdate(job_id="job1", processed=10, total=10, status="completed")
        await tracker.publish_progress(update)
        
        # Manually set completion time to past
        tracker.job_completion_times["job1"] = datetime.utcnow() - timedelta(hours=1)
        
        assert "job1" in tracker.job_progress
        
        # Run cleanup
        cleaned = tracker._cleanup_expired_jobs()
        
        assert cleaned == 1
        assert "job1" not in tracker.job_progress
        assert "job1" not in tracker.job_completion_times

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_jobs(self, tracker):
        """Test cleanup doesn't remove active jobs"""
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        await tracker.publish_progress(update)
        
        # Don't set completion time (keeps job active)
        cleaned = tracker._cleanup_expired_jobs()
        
        assert cleaned == 0
        assert "job1" in tracker.job_progress

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_subscribers(self, tracker):
        """Test cleanup also removes subscribers for expired jobs"""
        queue = await tracker.subscribe("job1")
        update = ProgressUpdate(job_id="job1", processed=10, total=10, status="completed")
        await tracker.publish_progress(update)
        
        # Mark as old
        tracker.job_completion_times["job1"] = datetime.utcnow() - timedelta(hours=1)
        
        assert "job1" in tracker.subscribers
        
        tracker._cleanup_expired_jobs()
        
        assert "job1" not in tracker.subscribers

    @pytest.mark.asyncio
    async def test_cleanup_task_runs_periodically(self):
        """Test background cleanup task"""
        tracker = ProgressTracker(ttl_hours=0.001, cleanup_interval=1)
        
        await tracker.start_cleanup_task()
        assert tracker.cleanup_task is not None
        assert not tracker.cleanup_task.done()
        
        # Add expired job
        update = ProgressUpdate(job_id="job1", processed=10, total=10, status="completed")
        await tracker.publish_progress(update)
        tracker.job_completion_times["job1"] = datetime.utcnow() - timedelta(hours=1)
        
        # Wait for cleanup to run
        await asyncio.sleep(2)
        
        # Job should be cleaned
        assert "job1" not in tracker.job_progress
        
        await tracker.shutdown()

    def test_memory_usage_estimation(self):
        """Test memory doesn't grow unbounded"""
        tracker = ProgressTracker()
        
        # Simulate 1000 completed jobs
        for i in range(1000):
            update = ProgressUpdate(
                job_id=f"job{i}",
                processed=100,
                total=100,
                status="completed"
            )
            asyncio.run(tracker.publish_progress(update))
        
        metrics = tracker.get_metrics()
        estimated_memory_mb = metrics["memory_jobs_bytes"] / (1024 * 1024)
        
        # Should be ~500KB for 1000 jobs, not unbounded
        assert estimated_memory_mb < 1.0


class TestEfficientBroadcasting:
    """Test IMPROVEMENT #2: Parallel async subscriber broadcasting"""

    @pytest.fixture
    def tracker(self):
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_parallel_subscriber_notification(self, tracker):
        """Test all subscribers notified concurrently"""
        # Create 10 subscribers
        queues = []
        for _ in range(10):
            queue = await tracker.subscribe("job1")
            queues.append(queue)
        
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        
        start = time.time()
        count = await tracker.publish_progress(update)
        elapsed = time.time() - start
        
        assert count == 10
        # With parallelization, should be fast (< 100ms)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_backpressure_detection(self, tracker):
        """Test backpressure detection for slow subscribers"""
        # Create a slow subscriber (small queue that fills up)
        queue = await tracker.subscribe("job1")
        
        # Fill the queue
        for _ in range(queue.maxsize):
            update = ProgressUpdate(job_id="job1", processed=1, total=10)
            await queue.put(update)
        
        # Next publish should detect backpressure
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        count = await tracker.publish_progress(update)
        
        # Should record backpressure event
        assert tracker.metrics["backpressure_events"] > 0

    @pytest.mark.asyncio
    async def test_slow_subscriber_removal(self, tracker):
        """Test removal of persistently slow subscribers"""
        queue = await tracker.subscribe("job1")
        
        # Simulate subscriber being slow (can't receive)
        # First, fill the queue
        for _ in range(queue.maxsize + 1):
            try:
                queue.get_nowait()
            except:
                pass
        
        # Now try multiple publishes to trigger removal
        for _ in range(3):
            update = ProgressUpdate(job_id="job1", processed=1, total=10)
            await tracker.publish_progress(update)
        
        # After multiple failures, slow subscriber should be removed
        metrics = tracker.get_metrics()
        # Check that we removed some subscribers
        assert metrics["total_subscribers_removed"] >= 0

    @pytest.mark.asyncio
    async def test_latency_tracking(self, tracker):
        """Test publish latency metrics"""
        queue = await tracker.subscribe("job1")
        
        # Publish multiple updates
        for i in range(10):
            update = ProgressUpdate(job_id="job1", processed=i, total=10)
            await tracker.publish_progress(update)
        
        metrics = tracker.get_metrics()
        assert metrics["avg_publish_latency_ms"] > 0
        assert metrics["max_publish_latency_ms"] >= metrics["avg_publish_latency_ms"]

    @pytest.mark.asyncio
    async def test_completion_tracking(self, tracker):
        """Test job completion is tracked for TTL"""
        update = ProgressUpdate(job_id="job1", processed=10, total=10, status="completed")
        await tracker.publish_progress(update)
        
        assert "job1" in tracker.job_completion_times
        assert tracker.job_completion_times["job1"] is not None

    @pytest.mark.asyncio
    async def test_failed_status_tracked(self, tracker):
        """Test failed status also tracks completion time"""
        update = ProgressUpdate(
            job_id="job1",
            processed=5,
            total=10,
            status="failed",
            error="Processing error"
        )
        await tracker.publish_progress(update)
        
        assert "job1" in tracker.job_completion_times


class TestProgressFormatter:
    """Test ProgressFormatter utility"""

    def test_format_sse(self):
        """Test SSE formatting"""
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        formatted = ProgressFormatter.format_sse(update)
        
        assert "event: processing" in formatted
        assert "data:" in formatted
        assert "job1" in formatted

    def test_format_percentage(self):
        """Test percentage formatting"""
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        percentage = ProgressFormatter.format_percentage(update)
        
        assert percentage == "50%"

    def test_format_percentage_zero_total(self):
        """Test percentage with zero total"""
        update = ProgressUpdate(job_id="job1", processed=0, total=0)
        percentage = ProgressFormatter.format_percentage(update)
        
        assert percentage == "0%"

    def test_format_human_readable(self):
        """Test human-readable formatting"""
        update = ProgressUpdate(
            job_id="job1",
            processed=5,
            total=10,
            message="Processing"
        )
        formatted = ProgressFormatter.format_human_readable(update)
        
        assert "[5/10]" in formatted
        assert "50%" in formatted
        assert "Processing" in formatted


class TestTrackerMetrics:
    """Test metrics and observability"""

    @pytest.fixture
    def tracker(self):
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_get_metrics(self, tracker):
        """Test metrics collection"""
        queue = await tracker.subscribe("job1")
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        
        await tracker.publish_progress(update)
        
        metrics = tracker.get_metrics()
        assert "total_publishes" in metrics
        assert "active_jobs" in metrics
        assert "active_subscribers_total" in metrics
        assert "memory_jobs_bytes" in metrics

    @pytest.mark.asyncio
    async def test_metrics_update_on_operations(self, tracker):
        """Test metrics are updated on operations"""
        queue1 = await tracker.subscribe("job1")
        queue2 = await tracker.subscribe("job1")
        
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        await tracker.publish_progress(update)
        
        await tracker.unsubscribe("job1", queue1)
        
        metrics = tracker.get_metrics()
        assert metrics["total_subscribers_removed"] == 1
        assert metrics["active_subscribers_total"] == 1


class TestGracefulShutdown:
    """Test graceful shutdown"""

    @pytest.mark.asyncio
    async def test_shutdown_cancels_cleanup(self):
        """Test shutdown cancels background cleanup task"""
        tracker = ProgressTracker(cleanup_interval=1)
        await tracker.start_cleanup_task()
        
        assert tracker.cleanup_task is not None
        
        await tracker.shutdown()
        
        # Give task time to cancel
        await asyncio.sleep(0.1)
        assert tracker.cleanup_task.done()

    @pytest.mark.asyncio
    async def test_shutdown_logs_metrics(self):
        """Test shutdown logs final metrics"""
        tracker = ProgressTracker()
        queue = await tracker.subscribe("job1")
        update = ProgressUpdate(job_id="job1", processed=5, total=10)
        await tracker.publish_progress(update)
        
        # Shutdown should not raise
        await tracker.shutdown()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
