"""
Optimized Batch Job Queue Management Service
Version 2.0 with memory management, efficient lookups, and error recovery
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueFullError(Exception):
    """Raised when queue reaches capacity"""
    pass


class RetryableError(Exception):
    """Raised for transient errors that should be retried"""
    pass


@dataclass
class BatchItem:
    """Represents a single item in a batch job"""
    id: str
    file: str
    prompt: str
    status: JobStatus = JobStatus.PENDING
    output_path: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    last_error_at: Optional[datetime] = None


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
    ttl_hours: int = 24
    # OPTIMIZATION: Cache progress metrics
    _completed_count: int = field(default=0, init=False)
    _failed_count: int = field(default=0, init=False)
    _metrics_cached_at: Optional[datetime] = field(default=None, init=False)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def will_expire_at(self) -> datetime:
        """Calculate expiration timestamp"""
        return self.created_at + timedelta(hours=self.ttl_hours)

    def is_expired(self) -> bool:
        """Check if job has expired"""
        return datetime.utcnow() > self.will_expire_at()


class BatchQueue:
    """
    Optimized async queue for managing batch jobs
    Features:
    - TTL-based automatic cleanup (prevents unbounded memory)
    - O(1) item lookups via item_index (vs O(n) linear search)
    - Cached progress metrics (vs recalculating per request)
    - Error recovery with retry logic
    """

    def __init__(
        self,
        max_concurrent_workers: int = 3,
        max_queue_size: int = 100,
        job_ttl_hours: int = 24,
        cleanup_interval_minutes: int = 10,
    ):
        """
        Initialize optimized batch queue

        Args:
            max_concurrent_workers: Number of concurrent processing workers
            max_queue_size: Maximum number of jobs in queue
            job_ttl_hours: Hours before completed/failed jobs expire
            cleanup_interval_minutes: Background cleanup task interval
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.jobs: Dict[str, BatchJob] = {}
        # OPTIMIZATION #1: Index for O(1) item lookup
        self.item_index: Dict[str, Tuple[str, int]] = {}  # item_id -> (job_id, item_idx)
        self.max_workers = max_concurrent_workers
        self.max_queue_size = max_queue_size
        self.job_ttl_hours = job_ttl_hours
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self.workers_running = False
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Started cleanup task (interval: {self.cleanup_interval_minutes}m)")

    async def stop(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped cleanup task")

    async def _cleanup_loop(self):
        """Background task: periodically cleanup expired jobs"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                removed = self.cleanup_old_jobs(hours=self.job_ttl_hours)
                if removed > 0:
                    logger.info(f"Cleanup: removed {removed} expired jobs")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def add_job(self, batch_job: BatchJob) -> str:
        """
        Add job to queue

        Args:
            batch_job: BatchJob instance

        Returns:
            Job ID

        Raises:
            QueueFullError: If queue is full
        """
        try:
            # Use put_nowait for immediate feedback, don't block
            self.queue.put_nowait(batch_job)
            self.jobs[batch_job.id] = batch_job
            # OPTIMIZATION #1: Build item_index for O(1) lookup
            for idx, item in enumerate(batch_job.items):
                self.item_index[item.id] = (batch_job.id, idx)
            logger.debug(f"Added job {batch_job.id} with {len(batch_job.items)} items")
            return batch_job.id
        except asyncio.QueueFull:
            raise QueueFullError(
                f"Batch queue is full ({self.queue.qsize()}/{self.max_queue_size}). "
                "Retry after 30 seconds."
            )

    async def get_job(self) -> Optional[BatchJob]:
        """Get next job from queue without blocking"""
        if not self.queue.empty():
            return await self.queue.get()
        return None

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of specific job"""
        job = self.jobs.get(job_id)
        if job and job.is_expired():
            logger.warning(f"Job {job_id} accessed but already expired")
            return None
        return job

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        processed_count: int = 0,
        total_size: int = 0,
    ) -> bool:
        """Update job status"""
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

        # Invalidate progress cache on status change
        job._metrics_cached_at = None
        return True

    def update_item_status(
        self,
        job_id: str,
        item_id: str,
        status: JobStatus,
        output_path: Optional[str] = None,
        error: Optional[str] = None,
        is_retryable: bool = False,
    ) -> bool:
        """
        Update individual item status within job
        OPTIMIZATION #1: O(1) lookup via item_index instead of O(n) search

        Args:
            job_id: Job ID
            item_id: Item ID
            status: New status
            output_path: Path to output file
            error: Error message if failed
            is_retryable: Whether error is transient and should be retried

        Returns:
            True if successful
        """
        if job_id not in self.jobs or item_id not in self.item_index:
            return False

        # OPTIMIZATION #1: O(1) lookup
        stored_job_id, item_idx = self.item_index[item_id]
        if stored_job_id != job_id:
            return False

        job = self.jobs[job_id]
        item = job.items[item_idx]

        item.status = status
        if output_path:
            item.output_path = output_path

        # OPTIMIZATION: Retry logic for transient errors
        if status == JobStatus.FAILED and is_retryable:
            if item.retry_count < 3:  # Max 3 retries
                item.retry_count += 1
                item.last_error_at = datetime.utcnow()
                item.status = JobStatus.PENDING
                logger.info(f"Retrying item {item_id} (attempt {item.retry_count}/3)")
                return True
            else:
                error = f"{error} (failed after 3 retries)" if error else "Max retries exceeded"

        if error:
            item.error = error
            item.last_error_at = datetime.utcnow()

        # Invalidate progress cache on item change
        job._metrics_cached_at = None
        return True

    def get_job_progress(self, job_id: str) -> Optional[Dict]:
        """
        Get progress information for job
        OPTIMIZATION #2: Cached metrics (updated on item changes)
        """
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]
        
        # OPTIMIZATION #2: Return cached metrics if still valid
        now = datetime.utcnow()
        if job._metrics_cached_at and (now - job._metrics_cached_at).total_seconds() < 5:
            return self._build_progress_dict(job, use_cache=True)

        # Recalculate metrics (invalidated on item changes)
        job._completed_count = sum(1 for item in job.items if item.status == JobStatus.COMPLETED)
        job._failed_count = sum(1 for item in job.items if item.status == JobStatus.FAILED)
        job._metrics_cached_at = now

        return self._build_progress_dict(job, use_cache=False)

    def _build_progress_dict(self, job: BatchJob, use_cache: bool = True) -> Dict:
        """Build progress dictionary with cached or fresh counts"""
        total = len(job.items)
        completed = job._completed_count if use_cache else sum(
            1 for item in job.items if item.status == JobStatus.COMPLETED
        )
        failed = job._failed_count if use_cache else sum(
            1 for item in job.items if item.status == JobStatus.FAILED
        )
        pending = total - completed - failed

        return {
            "job_id": job.id,
            "status": job.status.value,
            "total_items": total,
            "processed": completed,
            "failed": failed,
            "pending": pending,
            "progress_percent": int((completed / total) * 100) if total > 0 else 0,
            "total_size_bytes": job.total_size_bytes,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "expires_at": job.will_expire_at().isoformat(),
        }

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 20) -> List[Dict]:
        """List jobs with optional status filter"""
        jobs = [j for j in self.jobs.values() if not j.is_expired()]

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return [asdict(j) for j in jobs[:limit]]

    def cleanup_old_jobs(self, hours: int = 24) -> int:
        """
        Remove jobs older than specified hours
        OPTIMIZATION #3: TTL-based automatic cleanup prevents unbounded memory

        Args:
            hours: Age threshold in hours

        Returns:
            Number of jobs cleaned up
        """
        expired_job_ids = [job_id for job_id, job in self.jobs.items() if job.is_expired()]

        for job_id in expired_job_ids:
            job = self.jobs.pop(job_id)
            # Also cleanup item_index
            for item in job.items:
                self.item_index.pop(item.id, None)

        if expired_job_ids:
            logger.info(f"Cleaned up {len(expired_job_ids)} expired jobs")

        return len(expired_job_ids)

    def get_queue_stats(self) -> Dict:
        """Get comprehensive queue statistics"""
        jobs_list = list(self.jobs.values())
        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "total_tracked_jobs": len(jobs_list),
            "pending_jobs": sum(1 for j in jobs_list if j.status == JobStatus.PENDING),
            "processing_jobs": sum(1 for j in jobs_list if j.status == JobStatus.PROCESSING),
            "completed_jobs": sum(1 for j in jobs_list if j.status == JobStatus.COMPLETED),
            "failed_jobs": sum(1 for j in jobs_list if j.status == JobStatus.FAILED),
            "total_items": sum(len(j.items) for j in jobs_list),
            "item_index_size": len(self.item_index),
        }

    def queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def total_jobs(self) -> int:
        """Get total tracked jobs"""
        return len(self.jobs)
