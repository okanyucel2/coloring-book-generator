"""
Batch Processing API Routes
FastAPI/Flask endpoints for batch generation, progress tracking, and download management.
"""

from typing import List, Dict
import json
from datetime import datetime

# This is a reference implementation for batch API routes
# Integration with Flask/FastAPI framework happens in the main app


class BatchAPI:
    """Batch API endpoint handler"""

    def __init__(self, batch_queue, progress_tracker, zip_export_service):
        """
        Initialize batch API with services

        Args:
            batch_queue: BatchQueue instance
            progress_tracker: ProgressTracker instance
            zip_export_service: ZipExportService instance
        """
        self.queue = batch_queue
        self.progress = progress_tracker
        self.zip_service = zip_export_service

    async def submit_batch(self, payload: Dict) -> Dict:
        """
        Submit new batch job

        Args:
            payload: {
                "items": [{"file": str, "prompt": str}],
                "model": str,
                "options": {"quality": str, "include_pdf": bool}
            }

        Returns:
            {"batch_id": str, "status": str, "total_items": int}
        """
        try:
            from coloring_book.services import BatchJob, BatchItem

            # Validate payload
            if not payload.get("items"):
                return {"error": "No items in batch", "status": 400}

            items = []
            for item_data in payload["items"]:
                item = BatchItem(
                    id=f"item_{datetime.utcnow().timestamp()}",
                    file=item_data.get("file", "unknown"),
                    prompt=item_data.get("prompt", ""),
                )
                items.append(item)

            # Create batch job
            job = BatchJob(
                id=f"batch_{datetime.utcnow().timestamp()}",
                items=items,
                model=payload.get("model", "claude"),
                options=payload.get("options", {}),
            )

            # Add to queue
            batch_id = await self.queue.add_job(job)

            return {
                "status": 200,
                "batch_id": batch_id,
                "total_items": len(items),
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {"error": str(e), "status": 500}

    async def get_batch_progress(self, batch_id: str) -> Dict:
        """
        Get current batch progress

        Args:
            batch_id: Job ID

        Returns:
            Progress dict with processed count, total, percentage
        """
        progress = self.queue.get_job_progress(batch_id)

        if not progress:
            return {"error": "Batch not found", "status": 404}

        return {
            "status": 200,
            "progress": progress,
        }

    async def download_batch(self, batch_id: str) -> Dict:
        """
        Generate and prepare batch download

        Args:
            batch_id: Job ID

        Returns:
            {"zip_path": str, "size_bytes": int, "file_count": int}
        """
        job = self.queue.get_job_status(batch_id)

        if not job:
            return {"error": "Batch not found", "status": 404}

        # Prepare files for ZIP
        files_to_zip = []
        for item in job.items:
            if item.output_path:
                files_to_zip.append({
                    "path": item.output_path,
                    "arcname": item.file,
                })

        if not files_to_zip:
            return {"error": "No output files available", "status": 400}

        # Create ZIP
        zip_result = self.zip_service.create_zip(
            f"/tmp/batch_{batch_id}.zip",
            files_to_zip,
        )

        if zip_result["status"] != "success":
            return {"error": "ZIP creation failed", "status": 500}

        return {
            "status": 200,
            "zip_result": zip_result,
        }

    def list_batches(self, limit: int = 20) -> Dict:
        """
        List recent batch jobs

        Args:
            limit: Maximum jobs to return

        Returns:
            {"batches": [...], "count": int}
        """
        jobs = self.queue.list_jobs(limit=limit)

        return {
            "status": 200,
            "batches": jobs,
            "count": len(jobs),
        }

    async def cancel_batch(self, batch_id: str) -> Dict:
        """
        Cancel ongoing batch job

        Args:
            batch_id: Job ID

        Returns:
            {"status": int, "message": str}
        """
        from coloring_book.services import JobStatus

        success = self.queue.update_job_status(batch_id, JobStatus.CANCELLED)

        if not success:
            return {"error": "Batch not found", "status": 404}

        # Close all subscriptions
        await self.progress.close_all_subscriptions(batch_id)

        return {
            "status": 200,
            "message": f"Batch {batch_id} cancelled",
        }
