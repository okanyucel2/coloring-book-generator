"""
Batch Job Queue Management Service
Handles queue operations, job tracking, and state management for batch processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """Represents a single item in a batch job"""
    id: str
    file: str
    prompt: str
    status: JobStatus = JobStatus.PENDING
    output_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BatchJob:
    """Represents a complete batch job"""
    id: str
    items: List[BatchItem]
    model: str
    options: Dict
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processed_count: int = 0
    total_size_bytes: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class BatchQueue:
    """
    Async queue for managing batch jobs
    Supports concurrent processing with progress tracking
    """

    def __init__(self, max_concurrent_workers: int = 3, max_queue_size: int = 100):
        """
        Initialize batch queue

        Args:
            max_concurrent_workers: Number of concurrent processing workers
            max_queue_size: Maximum number of jobs in queue
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.jobs: Dict[str, BatchJob] = {}
        self.max_workers = max_concurrent_workers
        self.workers_running = False

    async def add_job(self, batch_job: BatchJob) -> str:
        """
        Add job to queue

        Args:
            batch_job: BatchJob instance

        Returns:
            Job ID

        Raises:
            asyncio.QueueFull: If queue is full
        """
        try:
            await self.queue.put(batch_job)
            self.jobs[batch_job.id] = batch_job
            return batch_job.id
        except asyncio.QueueFull:
            raise Exception("Batch queue is full. Please try again later.")

    async def get_job(self) -> Optional[BatchJob]:
        """Get next job from queue without blocking"""
        if not self.queue.empty():
            return await self.queue.get()
        return None

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """
        Get status of specific job

        Args:
            job_id: Job ID

        Returns:
            BatchJob instance or None if not found
        """
        return self.jobs.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        processed_count: int = 0,
        total_size: int = 0,
    ) -> bool:
        """
        Update job status

        Args:
            job_id: Job ID
            status: New status
            processed_count: Number of items processed
            total_size: Total output size in bytes

        Returns:
            True if successful, False if job not found
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        job.status = status

        if status == JobStatus.PROCESSING and job.started_at is None:
            job.started_at = datetime.utcnow()

        if status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()

        if processed_count > 0:
            job.processed_count = processed_count

        if total_size > 0:
            job.total_size_bytes = total_size

        return True

    def update_item_status(
        self, job_id: str, item_id: str, status: JobStatus, output_path: Optional[str] = None, error: Optional[str] = None
    ) -> bool:
        """
        Update individual item status within job

        Args:
            job_id: Job ID
            item_id: Item ID
            status: New status
            output_path: Path to output file
            error: Error message if failed

        Returns:
            True if successful
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        for item in job.items:
            if item.id == item_id:
                item.status = status
                if output_path:
                    item.output_path = output_path
                if error:
                    item.error = error
                return True

        return False

    def get_job_progress(self, job_id: str) -> Optional[Dict]:
        """
        Get progress information for job

        Args:
            job_id: Job ID

        Returns:
            Progress dict or None if job not found
        """
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        total = len(job.items)
        completed = sum(1 for item in job.items if item.status == JobStatus.COMPLETED)
        failed = sum(1 for item in job.items if item.status == JobStatus.FAILED)

        return {
            "job_id": job.id,
            "status": job.status.value,
            "total_items": total,
            "processed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "progress_percent": int((completed / total) * 100) if total > 0 else 0,
            "total_size_bytes": job.total_size_bytes,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 20) -> List[Dict]:
        """
        List jobs with optional status filter

        Args:
            status: Filter by status
            limit: Maximum number of jobs to return

        Returns:
            List of job dicts
        """
        jobs = list(self.jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return [asdict(j) for j in jobs[:limit]]

    def cleanup_old_jobs(self, hours: int = 24) -> int:
        """
        Remove jobs older than specified hours

        Args:
            hours: Age threshold in hours

        Returns:
            Number of jobs cleaned up
        """
        cutoff = datetime.utcnow()
        # In real implementation, would use timedelta
        old_jobs = [
            job_id
            for job_id, job in self.jobs.items()
            if job.completed_at and (cutoff - job.completed_at).total_seconds() > (hours * 3600)
        ]

        for job_id in old_jobs:
            del self.jobs[job_id]

        return len(old_jobs)

    def queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def total_jobs(self) -> int:
        """Get total tracked jobs"""
        return len(self.jobs)
