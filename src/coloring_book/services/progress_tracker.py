"""
Progress Tracking Service
Handles real-time progress updates via Server-Sent Events (SSE).
"""

import asyncio
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProgressUpdate:
    """Represents a progress update event"""
    job_id: str
    processed: int
    total: int
    current_item: str = ""
    message: str = ""
    status: str = "processing"  # processing, completed, failed
    error: Optional[str] = None
    total_size: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "processed": self.processed,
            "total": self.total,
            "current_item": self.current_item,
            "message": self.message,
            "status": self.status,
            "error": self.error,
            "total_size": self.total_size,
            "timestamp": self.timestamp.isoformat(),
        }


class ProgressTracker:
    """
    Tracks and broadcasts progress updates for batch jobs.
    Supports multiple subscribers per job.
    """

    def __init__(self):
        """Initialize progress tracker with empty subscribers dict"""
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.job_progress: Dict[str, ProgressUpdate] = {}

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        """
        Subscribe to progress updates for a job

        Args:
            job_id: Job ID to track

        Returns:
            asyncio.Queue for receiving updates
        """
        queue = asyncio.Queue()

        if job_id not in self.subscribers:
            self.subscribers[job_id] = []

        self.subscribers[job_id].append(queue)

        # Send last known progress immediately
        if job_id in self.job_progress:
            await queue.put(self.job_progress[job_id])

        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> bool:
        """
        Unsubscribe from progress updates

        Args:
            job_id: Job ID
            queue: Queue to remove

        Returns:
            True if successful
        """
        if job_id not in self.subscribers:
            return False

        if queue in self.subscribers[job_id]:
            self.subscribers[job_id].remove(queue)

            # Clean up empty subscriber lists
            if not self.subscribers[job_id]:
                del self.subscribers[job_id]

            return True

        return False

    async def publish_progress(self, update: ProgressUpdate) -> int:
        """
        Publish progress update to all subscribers

        Args:
            update: ProgressUpdate instance

        Returns:
            Number of subscribers notified
        """
        job_id = update.job_id
        self.job_progress[job_id] = update

        if job_id not in self.subscribers:
            return 0

        subscriber_count = 0

        for queue in self.subscribers[job_id]:
            try:
                await queue.put(update)
                subscriber_count += 1
            except asyncio.QueueFull:
                # Skip if queue is full
                continue

        return subscriber_count

    def get_latest_progress(self, job_id: str) -> Optional[ProgressUpdate]:
        """
        Get latest progress for a job without subscribing

        Args:
            job_id: Job ID

        Returns:
            Latest ProgressUpdate or None
        """
        return self.job_progress.get(job_id)

    def get_all_progress(self) -> Dict[str, Dict]:
        """
        Get all tracked progress as dicts

        Returns:
            Dict of job_id -> progress dict
        """
        return {
            job_id: update.to_dict()
            for job_id, update in self.job_progress.items()
        }

    def clear_job_progress(self, job_id: str) -> bool:
        """
        Clear progress tracking for job

        Args:
            job_id: Job ID

        Returns:
            True if found and cleared
        """
        if job_id in self.job_progress:
            del self.job_progress[job_id]
            return True

        return False

    def subscriber_count(self, job_id: str) -> int:
        """
        Get number of active subscribers for job

        Args:
            job_id: Job ID

        Returns:
            Number of subscribers
        """
        return len(self.subscribers.get(job_id, []))

    async def close_all_subscriptions(self, job_id: str):
        """
        Close all subscriptions for a job

        Args:
            job_id: Job ID
        """
        if job_id in self.subscribers:
            # Notify subscribers of completion
            queues = self.subscribers[job_id][:]

            for queue in queues:
                try:
                    # Send completion signal
                    await queue.put(None)  # None signals end of stream
                except asyncio.QueueFull:
                    continue

            del self.subscribers[job_id]


class ProgressFormatter:
    """Formats progress updates for different output formats"""

    @staticmethod
    def format_sse(update: ProgressUpdate) -> str:
        """
        Format progress update as Server-Sent Event

        Args:
            update: ProgressUpdate instance

        Returns:
            SSE formatted string
        """
        import json

        data = json.dumps(update.to_dict())
        event_type = update.status

        return f"event: {event_type}\ndata: {data}\n\n"

    @staticmethod
    def format_percentage(update: ProgressUpdate) -> str:
        """
        Format progress as percentage

        Args:
            update: ProgressUpdate instance

        Returns:
            Percentage string (e.g., "50%")
        """
        if update.total == 0:
            return "0%"

        percentage = int((update.processed / update.total) * 100)
        return f"{percentage}%"

    @staticmethod
    def format_human_readable(update: ProgressUpdate) -> str:
        """
        Format progress as human-readable string

        Args:
            update: ProgressUpdate instance

        Returns:
            Human-readable string
        """
        percentage = (
            int((update.processed / update.total) * 100)
            if update.total > 0
            else 0
        )
        return f"[{update.processed}/{update.total}] {percentage}% - {update.message}"
