"""
Unit tests for Batch Queue Management Service
Tests all critical paths: queue operations, job tracking, status updates.
Target: 90%+ code coverage
"""

import pytest
import asyncio
from datetime import datetime

from coloring_book.services.batch_queue import (
    BatchQueue,
    BatchJob,
    BatchItem,
    JobStatus,
)


class TestBatchItem:
    """Tests for BatchItem data class"""

    def test_batch_item_creation(self):
        """Should create batch item with all fields"""
        item = BatchItem(id="item_001", file="test.jpg", prompt="Test prompt")
        assert item.id == "item_001"
        assert item.file == "test.jpg"
        assert item.status == JobStatus.PENDING
        assert item.output_path is None

    def test_batch_item_with_error(self):
        """Should handle error state"""
        item = BatchItem(id="item_001", file="test.jpg", prompt="Prompt",
                        status=JobStatus.FAILED, error="File not found")
        assert item.status == JobStatus.FAILED
        assert item.error == "File not found"


class TestBatchJob:
    """Tests for BatchJob data class"""

    def test_batch_job_creation(self):
        """Should create batch job with timestamps"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        job = BatchJob(id="job_001", items=items, model="claude", options={"quality": "high"})
        assert job.id == "job_001"
        assert len(job.items) == 1
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None


class TestBatchQueue:
    """Tests for BatchQueue async queue management"""

    @pytest.fixture
    def queue(self):
        """Create fresh queue for each test"""
        return BatchQueue(max_concurrent_workers=2, max_queue_size=10)

    @pytest.fixture
    def sample_job(self):
        """Create sample batch job"""
        items = [BatchItem(id="1", file="a.jpg", prompt="p1")]
        return BatchJob(id="job_001", items=items, model="claude", options={"quality": "standard"})

    def test_queue_initialization(self, queue):
        """Should initialize queue with defaults"""
        assert queue.max_workers == 2
        assert queue.total_jobs() == 0

    def test_add_job_sync(self, queue, sample_job):
        """Should add job to queue synchronously"""
        async def add_and_check():
            job_id = await queue.add_job(sample_job)
            return job_id

        job_id = asyncio.run(add_and_check())
        assert job_id == "job_001"
        assert queue.total_jobs() == 1

    def test_get_job_status(self, queue, sample_job):
        """Should retrieve job by ID"""
        asyncio.run(queue.add_job(sample_job))
        job = queue.get_job_status("job_001")
        assert job is not None
        assert job.id == "job_001"
        assert job.status == JobStatus.PENDING

    def test_update_job_status(self, queue, sample_job):
        """Should update job status"""
        asyncio.run(queue.add_job(sample_job))
        success = queue.update_job_status("job_001", JobStatus.PROCESSING, 
                                         processed_count=1, total_size=1024)
        assert success is True
        job = queue.get_job_status("job_001")
        assert job.status == JobStatus.PROCESSING
        assert job.processed_count == 1

    def test_update_item_status(self, queue, sample_job):
        """Should update individual item in job"""
        asyncio.run(queue.add_job(sample_job))
        success = queue.update_item_status("job_001", "1", JobStatus.COMPLETED,
                                          output_path="/tmp/output1.png")
        assert success is True
        job = queue.get_job_status("job_001")
        item = next(i for i in job.items if i.id == "1")
        assert item.status == JobStatus.COMPLETED
        assert item.output_path == "/tmp/output1.png"

    def test_get_job_progress(self, queue, sample_job):
        """Should calculate progress metrics"""
        asyncio.run(queue.add_job(sample_job))
        progress = queue.get_job_progress("job_001")
        assert progress["job_id"] == "job_001"
        assert progress["status"] == "pending"
        assert progress["total_items"] == 1
        assert progress["processed"] == 0

    def test_progress_with_completed_items(self, queue, sample_job):
        """Should update progress as items complete"""
        asyncio.run(queue.add_job(sample_job))
        queue.update_item_status("job_001", "1", JobStatus.COMPLETED)
        queue.update_job_status("job_001", JobStatus.COMPLETED, processed_count=1)
        progress = queue.get_job_progress("job_001")
        assert progress["processed"] == 1
        assert progress["progress_percent"] == 100

    def test_list_jobs_all(self, queue, sample_job):
        """Should list all jobs"""
        asyncio.run(queue.add_job(sample_job))
        items = [BatchItem(id="3", file="c.jpg", prompt="p3")]
        job2 = BatchJob(id="job_002", items=items, model="gemini", options={})
        asyncio.run(queue.add_job(job2))
        jobs = queue.list_jobs()
        assert len(jobs) >= 2

    def test_queue_full_rejection(self, queue, sample_job):
        """Should reject job when queue is full"""
        queue_small = BatchQueue(max_queue_size=1)
        asyncio.run(queue_small.add_job(sample_job))
        items = [BatchItem(id="3", file="c.jpg", prompt="p3")]
        job2 = BatchJob(id="job_002", items=items, model="gemini", options={})

        with pytest.raises(Exception, match="queue is full"):
            asyncio.run(queue_small.add_job(job2))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
