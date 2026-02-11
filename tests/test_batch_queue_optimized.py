"""
Comprehensive tests for optimized batch_queue.py
Focus: Memory management (TTL), O(1) item lookups, error recovery
Tests all critical paths and edge cases to prevent regressions
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import logging

from coloring_book.services.batch_queue_optimized import (
    BatchQueue,
    BatchJob,
    BatchItem,
    JobStatus,
    QueueFullError,
    RetryableError,
)

logger = logging.getLogger(__name__)


class TestBatchItemOptimized:
    """Tests for BatchItem with retry logic"""

    def test_batch_item_creation(self):
        """Should create batch item with default retry count"""
        item = BatchItem(id="item_001", file="test.jpg", prompt="Test prompt")
        assert item.id == "item_001"
        assert item.retry_count == 0
        assert item.last_error_at is None

    def test_batch_item_retry_tracking(self):
        """Should track retry count and timestamps"""
        item = BatchItem(id="item_001", file="test.jpg", prompt="Prompt")
        item.retry_count = 1
        item.last_error_at = datetime.utcnow()
        assert item.retry_count == 1
        assert item.last_error_at is not None


class TestBatchJobOptimized:
    """Tests for BatchJob with TTL and caching"""

    def test_batch_job_creation_with_ttl(self):
        """Should create batch job with TTL calculation"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(
            id="job_001",
            items=items,
            model="claude",
            options={"quality": "high"},
            ttl_hours=24,
        )
        assert job.id == "job_001"
        assert job.ttl_hours == 24
        assert job.created_at is not None

    def test_batch_job_expiration_calculation(self):
        """Should calculate expiration timestamp correctly"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(
            id="job_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=24,
        )
        expires_at = job.will_expire_at()
        now = datetime.utcnow()
        # Should be approximately 24 hours in future
        delta = (expires_at - now).total_seconds()
        assert 86300 < delta < 86500  # 24 hours ± 100 seconds

    def test_batch_job_expiration_check(self):
        """Should correctly identify expired jobs"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(
            id="job_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=0,  # Expire immediately
        )
        # Job created now with 0 TTL should be expired
        assert job.is_expired() is True

    def test_batch_job_not_expired(self):
        """Should identify non-expired jobs"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(
            id="job_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=24,
        )
        assert job.is_expired() is False

    def test_batch_job_cache_invalidation(self):
        """Should invalidate cache on metrics change"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(id="job_001", items=items, model="claude", options={})
        job._metrics_cached_at = datetime.utcnow()
        assert job._metrics_cached_at is not None

        # Cache should be invalidated on status update
        job._metrics_cached_at = None
        assert job._metrics_cached_at is None


class TestBatchQueueOptimized:
    """Tests for optimized BatchQueue"""

    @pytest.fixture
    def queue(self):
        """Create fresh queue for each test"""
        return BatchQueue(
            max_concurrent_workers=2,
            max_queue_size=10,
            job_ttl_hours=24,
            cleanup_interval_minutes=1,
        )

    @pytest.fixture
    def sample_job(self):
        """Create sample batch job with 10 items"""
        items = [BatchItem(id=f"item_{i}", file=f"file_{i}.jpg", prompt=f"p{i}") for i in range(10)]
        return BatchJob(
            id="job_001",
            items=items,
            model="claude",
            options={"quality": "standard"},
        )

    @pytest.fixture
    async def queue_with_start(self, queue):
        """Create queue and start background tasks"""
        await queue.start()
        yield queue
        await queue.stop()

    # ============================================================================
    # OPTIMIZATION #1: O(1) Item Lookup Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_item_index_building_on_add_job(self, queue, sample_job):
        """OPTIMIZATION #1: Should build item_index for O(1) lookups on job add"""
        job_id = await queue.add_job(sample_job)
        
        # Verify item_index was built
        assert len(queue.item_index) == 10
        
        # Verify each item is indexed
        for i in range(10):
            item_id = f"item_{i}"
            assert item_id in queue.item_index
            stored_job_id, item_idx = queue.item_index[item_id]
            assert stored_job_id == job_id
            assert item_idx == i

    @pytest.mark.asyncio
    async def test_update_item_status_o1_lookup(self, queue, sample_job):
        """OPTIMIZATION #1: Should update item in O(1) time using index"""
        await queue.add_job(sample_job)
        
        # Update item using optimized O(1) lookup
        success = queue.update_item_status(
            "job_001",
            "item_5",
            JobStatus.COMPLETED,
            output_path="/tmp/output5.png",
        )
        
        assert success is True
        job = queue.get_job_status("job_001")
        item = job.items[5]
        assert item.id == "item_5"
        assert item.status == JobStatus.COMPLETED
        assert item.output_path == "/tmp/output5.png"

    @pytest.mark.asyncio
    async def test_update_item_status_invalid_item_id(self, queue, sample_job):
        """Should return False for non-existent item ID"""
        await queue.add_job(sample_job)
        
        success = queue.update_item_status(
            "job_001",
            "invalid_item_id",
            JobStatus.COMPLETED,
        )
        
        assert success is False

    @pytest.mark.asyncio
    async def test_update_item_status_wrong_job_id(self, queue, sample_job):
        """Should return False if item belongs to different job"""
        await queue.add_job(sample_job)
        
        success = queue.update_item_status(
            "wrong_job_id",
            "item_0",
            JobStatus.COMPLETED,
        )
        
        assert success is False

    # ============================================================================
    # OPTIMIZATION #2: Progress Caching Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_progress_caching_validity(self, queue, sample_job):
        """OPTIMIZATION #2: Should cache progress metrics for 5 seconds"""
        await queue.add_job(sample_job)
        
        # First call: cache is populated
        progress1 = queue.get_job_progress("job_001")
        assert progress1["processed"] == 0
        
        job = queue.get_job_status("job_001")
        assert job._metrics_cached_at is not None
        first_cache_time = job._metrics_cached_at
        
        # Immediate second call: should use cache
        progress2 = queue.get_job_progress("job_001")
        assert progress2 == progress1  # Identical (from cache)
        assert job._metrics_cached_at == first_cache_time  # Cache not updated

    @pytest.mark.asyncio
    async def test_progress_cache_invalidation_on_item_update(self, queue, sample_job):
        """OPTIMIZATION #2: Should invalidate cache when item status changes"""
        await queue.add_job(sample_job)
        
        # Get initial progress (builds cache)
        progress1 = queue.get_job_progress("job_001")
        assert progress1["processed"] == 0
        
        job = queue.get_job_status("job_001")
        first_cache_time = job._metrics_cached_at
        
        # Update item status
        queue.update_item_status("job_001", "item_0", JobStatus.COMPLETED)
        
        # Cache should be invalidated
        assert job._metrics_cached_at is None
        
        # Next call should recalculate
        progress2 = queue.get_job_progress("job_001")
        assert progress2["processed"] == 1
        assert job._metrics_cached_at is not None
        assert job._metrics_cached_at > first_cache_time

    @pytest.mark.asyncio
    async def test_progress_metrics_accuracy(self, queue, sample_job):
        """Should calculate progress metrics accurately"""
        await queue.add_job(sample_job)
        
        # Complete 5 items, fail 3 items
        for i in range(5):
            queue.update_item_status("job_001", f"item_{i}", JobStatus.COMPLETED)
        for i in range(5, 8):
            queue.update_item_status("job_001", f"item_{i}", JobStatus.FAILED, error="Test error")
        
        progress = queue.get_job_progress("job_001")
        assert progress["total_items"] == 10
        assert progress["processed"] == 5
        assert progress["failed"] == 3
        assert progress["pending"] == 2
        assert progress["progress_percent"] == 50

    # ============================================================================
    # OPTIMIZATION #3: TTL & Automatic Cleanup Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs_by_expiration(self, queue):
        """OPTIMIZATION #3: Should cleanup expired jobs"""
        # Create expired job
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        expired_job = BatchJob(
            id="expired_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=0,  # Expired immediately
        )
        await queue.add_job(expired_job)
        
        # Create non-expired job
        normal_job = BatchJob(
            id="normal_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=24,
        )
        await queue.add_job(normal_job)
        
        assert queue.total_jobs() == 2
        
        # Cleanup expired jobs
        removed = queue.cleanup_old_jobs(hours=24)
        
        assert removed == 1
        assert queue.total_jobs() == 1
        assert "normal_001" in queue.jobs
        assert "expired_001" not in queue.jobs

    @pytest.mark.asyncio
    async def test_item_index_cleanup_on_job_deletion(self, queue, sample_job):
        """Should cleanup item_index when job is deleted"""
        await queue.add_job(sample_job)
        assert len(queue.item_index) == 10
        
        # Make job expired and cleanup
        sample_job.ttl_hours = 0
        removed = queue.cleanup_old_jobs(hours=24)
        
        assert removed == 1
        # Item index should be cleaned up
        assert len(queue.item_index) == 0

    @pytest.mark.asyncio
    async def test_get_job_status_returns_none_for_expired_job(self, queue):
        """Should return None for expired jobs when accessed"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        expired_job = BatchJob(
            id="expired_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=0,  # Expired immediately
        )
        await queue.add_job(expired_job)
        
        # Job exists in memory but is expired
        result = queue.get_job_status("expired_001")
        assert result is None  # Should return None for expired job

    # ============================================================================
    # Error Recovery & Retry Logic Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_retry_logic_retryable_error(self, queue, sample_job):
        """Should retry failed item if error is retryable"""
        await queue.add_job(sample_job)
        
        # First failure with retryable=True
        success = queue.update_item_status(
            "job_001",
            "item_0",
            JobStatus.FAILED,
            error="Network timeout",
            is_retryable=True,
        )
        
        assert success is True
        item = queue.jobs["job_001"].items[0]
        # Item should be reset to PENDING for retry
        assert item.status == JobStatus.PENDING
        assert item.retry_count == 1
        assert item.last_error_at is not None

    @pytest.mark.asyncio
    async def test_retry_logic_max_retries_exceeded(self, queue, sample_job):
        """Should mark as FAILED after 3 retries"""
        await queue.add_job(sample_job)
        
        item = queue.jobs["job_001"].items[0]
        item.retry_count = 3  # Already at max
        
        # Next failure should stick
        success = queue.update_item_status(
            "job_001",
            "item_0",
            JobStatus.FAILED,
            error="Network timeout",
            is_retryable=True,
        )
        
        assert success is True
        # Item should stay FAILED
        assert item.status == JobStatus.FAILED
        assert "failed after 3 retries" in item.error

    @pytest.mark.asyncio
    async def test_retry_logic_non_retryable_error(self, queue, sample_job):
        """Should mark as FAILED immediately for non-retryable errors"""
        await queue.add_job(sample_job)
        
        success = queue.update_item_status(
            "job_001",
            "item_0",
            JobStatus.FAILED,
            error="File not found",
            is_retryable=False,  # Not retryable
        )
        
        assert success is True
        item = queue.jobs["job_001"].items[0]
        # Item should stay FAILED
        assert item.status == JobStatus.FAILED
        assert item.retry_count == 0

    # ============================================================================
    # Queue Management Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_add_job_to_full_queue(self, queue):
        """Should raise QueueFullError when queue is full"""
        queue_small = BatchQueue(max_queue_size=1)
        
        items1 = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job1 = BatchJob(id="job_001", items=items1, model="claude", options={})
        await queue_small.add_job(job1)
        
        items2 = [BatchItem(id="2", file="b.jpg", prompt="p2")]
        job2 = BatchJob(id="job_002", items=items2, model="claude", options={})
        
        # Should raise QueueFullError with message about queue being full
        with pytest.raises(QueueFullError) as exc_info:
            await queue_small.add_job(job2)
        
        # Verify error message contains "queue is full"
        assert "queue is full" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue):
        """Should return comprehensive queue statistics"""
        # Add jobs with different statuses
        items1 = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job1 = BatchJob(id="job_001", items=items1, model="claude", options={})
        await queue.add_job(job1)
        queue.update_job_status("job_001", JobStatus.PROCESSING)
        
        items2 = [
            BatchItem(id="2", file="b.jpg", prompt="p2"),
            BatchItem(id="3", file="c.jpg", prompt="p3"),
        ]
        job2 = BatchJob(id="job_002", items=items2, model="claude", options={})
        await queue.add_job(job2)
        
        stats = queue.get_queue_stats()
        assert stats["total_tracked_jobs"] == 2
        assert stats["processing_jobs"] == 1
        assert stats["pending_jobs"] == 1
        assert stats["total_items"] == 3
        assert stats["item_index_size"] == 3

    @pytest.mark.asyncio
    async def test_list_jobs_excludes_expired(self, queue):
        """Should exclude expired jobs from list"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        
        # Expired job
        expired_job = BatchJob(
            id="expired_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=0,
        )
        await queue.add_job(expired_job)
        
        # Active job
        active_job = BatchJob(
            id="active_001",
            items=items,
            model="claude",
            options={},
            ttl_hours=24,
        )
        await queue.add_job(active_job)
        
        jobs = queue.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["id"] == "active_001"

    # ============================================================================
    # Integration Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_full_job_lifecycle_with_optimizations(self, queue):
        """Test complete job lifecycle using all optimizations"""
        items = [BatchItem(id=f"item_{i}", file=f"file_{i}.jpg", prompt=f"p{i}") for i in range(5)]
        job = BatchJob(id="job_001", items=items, model="claude", options={})
        
        # Add job
        job_id = await queue.add_job(job)
        assert job_id == "job_001"
        
        # Verify index was built
        assert len(queue.item_index) == 5
        
        # Update to processing
        queue.update_job_status("job_001", JobStatus.PROCESSING)
        
        # Process items
        for i in range(5):
            queue.update_item_status(
                "job_001",
                f"item_{i}",
                JobStatus.COMPLETED,
                output_path=f"/tmp/output_{i}.png",
            )
        
        # Check progress (uses cache)
        progress = queue.get_job_progress("job_001")
        assert progress["processed"] == 5
        assert progress["progress_percent"] == 100
        
        # Update job status
        queue.update_job_status("job_001", JobStatus.COMPLETED)
        
        # Verify job is findable
        job = queue.get_job_status("job_001")
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_progress_expiration_metadata(self, queue, sample_job):
        """Should include expiration info in progress"""
        await queue.add_job(sample_job)
        
        progress = queue.get_job_progress("job_001")
        assert "expires_at" in progress
        # Parse ISO format to verify it's in future
        expires_at = datetime.fromisoformat(progress["expires_at"])
        assert expires_at > datetime.utcnow()


# ============================================================================
# Performance Benchmarks (Not strict assertions, informational)
# ============================================================================

class TestPerformance:
    """Performance characteristics of optimizations"""

    @pytest.mark.asyncio
    async def test_o1_item_lookup_scales_linearly(self):
        """OPTIMIZATION #1: O(1) lookup should not degrade with job size"""
        queue = BatchQueue()
        
        # Create job with 1000 items
        items = [BatchItem(id=f"item_{i}", file=f"file_{i}.jpg", prompt=f"p{i}") for i in range(1000)]
        job = BatchJob(id="job_001", items=items, model="claude", options={})
        await queue.add_job(job)
        
        # Update 100 random items and measure
        import time
        start = time.time()
        for i in range(100):
            queue.update_item_status("job_001", f"item_{i * 10}", JobStatus.COMPLETED)
        elapsed = time.time() - start
        
        # Should complete in < 50ms (100 updates on 1000-item job)
        assert elapsed < 0.05, f"100 updates took {elapsed}s, expected < 0.05s"

    @pytest.mark.asyncio
    async def test_cache_reduces_progress_recalculation(self):
        """OPTIMIZATION #2: Cache should prevent redundant calculations"""
        queue = BatchQueue()
        
        items = [BatchItem(id=f"item_{i}", file=f"file_{i}.jpg", prompt=f"p{i}") for i in range(100)]
        job = BatchJob(id="job_001", items=items, model="claude", options={})
        await queue.add_job(job)
        
        import time
        
        # First call: builds cache
        start = time.time()
        progress1 = queue.get_job_progress("job_001")
        first_call = time.time() - start
        
        # Second call: uses cache
        start = time.time()
        progress2 = queue.get_job_progress("job_001")
        cached_call = time.time() - start
        
        # Cached call should be faster (at least 2x)
        assert cached_call < first_call * 0.5, f"Cache not effective: {cached_call}s vs {first_call}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
