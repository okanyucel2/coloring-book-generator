"""
Integration Test: Old vs New Service Implementations
Verifies that optimized services (progress_tracker_optimized, batch_queue_optimized)
work identically to original implementations in batch_routes.py context
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# Import original implementations
from coloring_book.services.progress_tracker import (
    ProgressTracker as ProgressTrackerOriginal,
    ProgressUpdate,
)
from coloring_book.services.batch_queue import (
    BatchQueue as BatchQueueOriginal,
    BatchJob,
    BatchItem,
    JobStatus,
)

# Import optimized implementations (when available)
try:
    from coloring_book.services.progress_tracker_optimized import (
        ProgressTracker as ProgressTrackerOptimized,
    )
except ImportError:
    ProgressTrackerOptimized = None

try:
    from coloring_book.services.batch_queue_optimized import (
        BatchQueue as BatchQueueOptimized,
    )
except ImportError:
    BatchQueueOptimized = None


class TestProgressTrackerCompatibility:
    """Test that optimized progress tracker maintains API compatibility"""

    @pytest.fixture
    async def tracker_original(self):
        """Create original progress tracker"""
        return ProgressTrackerOriginal()

    @pytest.fixture
    async def tracker_optimized(self):
        """Create optimized progress tracker if available"""
        if ProgressTrackerOptimized is None:
            pytest.skip("Optimized tracker not available")
        return ProgressTrackerOptimized()

    @pytest.mark.asyncio
    async def test_subscribe_identical(self, tracker_original, tracker_optimized):
        """Test subscribe() works identically on both versions"""
        job_id = "test_job_1"

        # Subscribe on original
        queue_orig = await tracker_original.subscribe(job_id)
        assert isinstance(queue_orig, asyncio.Queue)

        # Subscribe on optimized
        queue_opt = await tracker_optimized.subscribe(job_id)
        assert isinstance(queue_opt, asyncio.Queue)

        # Both should return queues
        assert queue_orig is not None
        assert queue_opt is not None

    @pytest.mark.asyncio
    async def test_unsubscribe_identical(self, tracker_original, tracker_optimized):
        """Test unsubscribe() works identically on both versions"""
        job_id = "test_job_2"

        # Subscribe and unsubscribe on original
        queue_orig = await tracker_original.subscribe(job_id)
        result_orig = await tracker_original.unsubscribe(job_id, queue_orig)
        assert result_orig is True

        # Subscribe and unsubscribe on optimized
        queue_opt = await tracker_optimized.subscribe(job_id)
        result_opt = await tracker_optimized.unsubscribe(job_id, queue_opt)
        assert result_opt is True

    @pytest.mark.asyncio
    async def test_publish_progress_identical(self, tracker_original, tracker_optimized):
        """Test publish_progress() behavior is identical"""
        job_id = "test_job_3"

        # Subscribe on both
        queue_orig = await tracker_original.subscribe(job_id)
        queue_opt = await tracker_optimized.subscribe(job_id)

        # Create update
        update = ProgressUpdate(
            job_id=job_id,
            processed=5,
            total=10,
            message="Processing items",
            status="processing",
        )

        # Publish on both
        count_orig = await tracker_original.publish_progress(update)
        count_opt = await tracker_optimized.publish_progress(update)

        # Should notify same number of subscribers
        assert count_orig == 1  # Only one subscriber on original
        assert count_opt == 1  # Only one subscriber on optimized

    @pytest.mark.asyncio
    async def test_get_latest_progress_identical(
        self, tracker_original, tracker_optimized
    ):
        """Test get_latest_progress() returns identical data"""
        job_id = "test_job_4"

        update = ProgressUpdate(
            job_id=job_id,
            processed=3,
            total=10,
            message="Test",
            status="processing",
        )

        # Publish and retrieve on original
        await tracker_original.publish_progress(update)
        result_orig = tracker_original.get_latest_progress(job_id)

        # Publish and retrieve on optimized
        await tracker_optimized.publish_progress(update)
        result_opt = tracker_optimized.get_latest_progress(job_id)

        # Results should be equivalent
        assert result_orig.job_id == result_opt.job_id
        assert result_orig.processed == result_opt.processed
        assert result_orig.total == result_opt.total

    @pytest.mark.asyncio
    async def test_get_all_progress_identical(self, tracker_original, tracker_optimized):
        """Test get_all_progress() returns identical structure"""
        job_ids = ["job_a", "job_b", "job_c"]

        for job_id in job_ids:
            update = ProgressUpdate(
                job_id=job_id,
                processed=1,
                total=5,
                status="processing",
            )
            await tracker_original.publish_progress(update)
            await tracker_optimized.publish_progress(update)

        # Get all progress from both
        all_orig = tracker_original.get_all_progress()
        all_opt = tracker_optimized.get_all_progress()

        # Both should have same job IDs
        assert set(all_orig.keys()) == set(all_opt.keys())
        assert len(all_orig) >= 3
        assert len(all_opt) >= 3

    @pytest.mark.asyncio
    async def test_subscriber_count_identical(
        self, tracker_original, tracker_optimized
    ):
        """Test subscriber_count() returns identical counts"""
        job_id = "test_job_5"

        # Add multiple subscribers on original
        await tracker_original.subscribe(job_id)
        await tracker_original.subscribe(job_id)
        count_orig = tracker_original.subscriber_count(job_id)

        # Add same number of subscribers on optimized
        await tracker_optimized.subscribe(job_id)
        await tracker_optimized.subscribe(job_id)
        count_opt = tracker_optimized.subscriber_count(job_id)

        # Should have identical counts
        assert count_orig == count_opt == 2

    @pytest.mark.asyncio
    async def test_clear_job_progress_identical(
        self, tracker_original, tracker_optimized
    ):
        """Test clear_job_progress() works identically"""
        job_id = "test_job_6"

        # Set progress on both
        update = ProgressUpdate(
            job_id=job_id,
            processed=5,
            total=10,
            status="processing",
        )
        await tracker_original.publish_progress(update)
        await tracker_optimized.publish_progress(update)

        # Verify progress exists
        assert tracker_original.get_latest_progress(job_id) is not None
        assert tracker_optimized.get_latest_progress(job_id) is not None

        # Clear on both
        cleared_orig = tracker_original.clear_job_progress(job_id)
        cleared_opt = tracker_optimized.clear_job_progress(job_id)

        # Both should succeed
        assert cleared_orig is True
        assert cleared_opt is True

        # Progress should be gone
        assert tracker_original.get_latest_progress(job_id) is None
        assert tracker_optimized.get_latest_progress(job_id) is None


class TestBatchQueueCompatibility:
    """Test that optimized batch queue maintains API compatibility"""

    @pytest.fixture
    def queue_original(self):
        """Create original batch queue"""
        return BatchQueueOriginal(max_concurrent_workers=3, max_queue_size=100)

    @pytest.fixture
    def queue_optimized(self):
        """Create optimized batch queue if available"""
        if BatchQueueOptimized is None:
            pytest.skip("Optimized queue not available")
        return BatchQueueOptimized(max_concurrent_workers=3, max_queue_size=100)

    def _create_test_job(self, job_id: str) -> BatchJob:
        """Helper to create test batch job"""
        items = [
            BatchItem(id="item_1", file="file1.png", prompt="prompt1"),
            BatchItem(id="item_2", file="file2.png", prompt="prompt2"),
            BatchItem(id="item_3", file="file3.png", prompt="prompt3"),
        ]
        return BatchJob(
            id=job_id,
            items=items,
            model="claude",
            options={"quality": "high"},
        )

    @pytest.mark.asyncio
    async def test_add_job_identical(self, queue_original, queue_optimized):
        """Test add_job() works identically"""
        job = self._create_test_job("job_1")

        # Add to original
        job_id_orig = await queue_original.add_job(job)
        assert job_id_orig == job.id

        # Add to optimized
        job = self._create_test_job("job_2")
        job_id_opt = await queue_optimized.add_job(job)
        assert job_id_opt == job.id

    @pytest.mark.asyncio
    async def test_get_job_status_identical(self, queue_original, queue_optimized):
        """Test get_job_status() returns identical data"""
        job = self._create_test_job("job_3")

        # Add job to both
        await queue_original.add_job(job)
        await queue_optimized.add_job(job)

        # Get status from both
        status_orig = queue_original.get_job_status(job.id)
        status_opt = queue_optimized.get_job_status(job.id)

        # Should have same structure
        assert status_orig.id == status_opt.id
        assert status_orig.status == status_opt.status
        assert len(status_orig.items) == len(status_opt.items)

    @pytest.mark.asyncio
    async def test_update_job_status_identical(self, queue_original, queue_optimized):
        """Test update_job_status() works identically"""
        job = self._create_test_job("job_4")

        # Add to both
        await queue_original.add_job(job)
        await queue_optimized.add_job(job)

        # Update on original
        result_orig = queue_original.update_job_status(
            job.id,
            JobStatus.PROCESSING,
            processed_count=2,
        )

        # Update on optimized
        result_opt = queue_optimized.update_job_status(
            job.id,
            JobStatus.PROCESSING,
            processed_count=2,
        )

        # Both should succeed
        assert result_orig is True
        assert result_opt is True

        # Verify status changed
        status_orig = queue_original.get_job_status(job.id)
        status_opt = queue_optimized.get_job_status(job.id)
        assert status_orig.status == JobStatus.PROCESSING
        assert status_opt.status == JobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_get_job_progress_identical(self, queue_original, queue_optimized):
        """Test get_job_progress() returns identical structure"""
        job = self._create_test_job("job_5")

        # Add to both
        await queue_original.add_job(job)
        await queue_optimized.add_job(job)

        # Update progress on both
        await queue_original.update_job_status(
            job.id,
            JobStatus.PROCESSING,
            processed_count=1,
        )
        await queue_optimized.update_job_status(
            job.id,
            JobStatus.PROCESSING,
            processed_count=1,
        )

        # Get progress from both
        progress_orig = queue_original.get_job_progress(job.id)
        progress_opt = queue_optimized.get_job_progress(job.id)

        # Should have identical structure
        assert progress_orig["job_id"] == progress_opt["job_id"]
        assert progress_orig["status"] == progress_opt["status"]
        assert progress_orig["total_items"] == progress_opt["total_items"]
        assert progress_orig["processed"] == progress_opt["processed"]

    @pytest.mark.asyncio
    async def test_update_item_status_identical(
        self, queue_original, queue_optimized
    ):
        """Test update_item_status() works identically"""
        job = self._create_test_job("job_6")
        item_id = "item_1"
        output_path = "/tmp/output_1.png"

        # Add to both
        await queue_original.add_job(job)
        await queue_optimized.add_job(job)

        # Update item on original
        result_orig = queue_original.update_item_status(
            job.id,
            item_id,
            JobStatus.COMPLETED,
            output_path=output_path,
        )

        # Update item on optimized
        result_opt = queue_optimized.update_item_status(
            job.id,
            item_id,
            JobStatus.COMPLETED,
            output_path=output_path,
        )

        # Both should succeed
        assert result_orig is True
        assert result_opt is True

        # Verify item updated on both
        status_orig = queue_original.get_job_status(job.id)
        status_opt = queue_optimized.get_job_status(job.id)

        item_orig = next((i for i in status_orig.items if i.id == item_id), None)
        item_opt = next((i for i in status_opt.items if i.id == item_id), None)

        assert item_orig.status == JobStatus.COMPLETED
        assert item_opt.status == JobStatus.COMPLETED
        assert item_orig.output_path == output_path
        assert item_opt.output_path == output_path

    @pytest.mark.asyncio
    async def test_list_jobs_identical(self, queue_original, queue_optimized):
        """Test list_jobs() returns identical data"""
        # Add multiple jobs
        for i in range(3):
            job = self._create_test_job(f"job_list_{i}")
            await queue_original.add_job(job)
            await queue_optimized.add_job(job)

        # List jobs from both
        jobs_orig = queue_original.list_jobs(limit=10)
        jobs_opt = queue_optimized.list_jobs(limit=10)

        # Should have same count
        assert len(jobs_orig) >= 3
        assert len(jobs_opt) >= 3

        # Should have identical structure
        for i, (orig, opt) in enumerate(zip(jobs_orig[:3], jobs_opt[:3])):
            assert orig["id"] == opt["id"]
            assert orig["status"] == opt["status"]

    @pytest.mark.asyncio
    async def test_queue_size_identical(self, queue_original, queue_optimized):
        """Test queue_size() returns identical counts"""
        # Add jobs to both
        for i in range(3):
            job = self._create_test_job(f"job_size_{i}")
            await queue_original.add_job(job)
            await queue_optimized.add_job(job)

        # Get queue sizes
        size_orig = queue_original.queue_size()
        size_opt = queue_optimized.queue_size()

        # Should have same size (accounting for async timing)
        assert abs(size_orig - size_opt) <= 1

    @pytest.mark.asyncio
    async def test_total_jobs_identical(self, queue_original, queue_optimized):
        """Test total_jobs() returns identical counts"""
        # Add jobs to both
        for i in range(5):
            job = self._create_test_job(f"job_total_{i}")
            await queue_original.add_job(job)
            await queue_optimized.add_job(job)

        # Get total jobs
        total_orig = queue_original.total_jobs()
        total_opt = queue_optimized.total_jobs()

        # Should have same total
        assert total_orig >= 5
        assert total_opt >= 5
        assert total_orig == total_opt


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    @pytest.mark.asyncio
    async def test_batch_api_workflow_compatible(self):
        """Test a realistic batch processing workflow works with both versions"""
        # Original implementations
        progress_orig = ProgressTrackerOriginal()
        queue_orig = BatchQueueOriginal(max_concurrent_workers=2)

        # Optimized implementations
        if ProgressTrackerOptimized is None or BatchQueueOptimized is None:
            pytest.skip("Optimized versions not available")

        progress_opt = ProgressTrackerOptimized()
        queue_opt = BatchQueueOptimized(max_concurrent_workers=2)

        # Test workflow: submit job -> track progress
        job = BatchJob(
            id="workflow_job",
            items=[
                BatchItem(id="w_1", file="f1.png", prompt="p1"),
                BatchItem(id="w_2", file="f2.png", prompt="p2"),
            ],
            model="claude",
            options={},
        )

        # Submit to both
        await queue_orig.add_job(job)
        await queue_opt.add_job(job)

        # Track progress on both
        sub_orig = await progress_orig.subscribe("workflow_job")
        sub_opt = await progress_opt.subscribe("workflow_job")

        # Update progress
        update = ProgressUpdate(
            job_id="workflow_job",
            processed=1,
            total=2,
            status="processing",
        )

        count_orig = await progress_orig.publish_progress(update)
        count_opt = await progress_opt.publish_progress(update)

        # Both should notify 1 subscriber
        assert count_orig == 1
        assert count_opt == 1

        # Check progress
        progress_orig_val = progress_orig.get_latest_progress("workflow_job")
        progress_opt_val = progress_opt.get_latest_progress("workflow_job")

        assert progress_orig_val.processed == progress_opt_val.processed == 1
        assert progress_orig_val.total == progress_opt_val.total == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
