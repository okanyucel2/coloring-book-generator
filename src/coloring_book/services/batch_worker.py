"""Async batch worker that processes queued batch jobs.

Polls BatchQueue for pending jobs, generates coloring pages using
WorkbookImageGenerator, publishes progress via ProgressTracker,
and creates ZIP exports on completion.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from .batch_queue_optimized import BatchQueue, JobStatus, RetryableError
from .progress_tracker_optimized import ProgressTracker, ProgressUpdate
from .zip_export import ZipExportService

logger = logging.getLogger(__name__)

# Output directory for generated images
OUTPUT_DIR = Path(tempfile.gettempdir()) / "coloring_book_batch"


async def batch_worker(
    queue: BatchQueue,
    tracker: ProgressTracker,
    zip_service: ZipExportService,
    poll_interval: float = 1.0,
) -> None:
    """Background worker that processes batch jobs from the queue.

    Args:
        queue: BatchQueue to poll for jobs.
        tracker: ProgressTracker for SSE broadcasting.
        zip_service: ZipExportService for creating ZIP downloads.
        poll_interval: Seconds between queue polls when idle.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Batch worker started")

    try:
        while True:
            job = await queue.get_job()

            if job is None:
                await asyncio.sleep(poll_interval)
                continue

            await _process_job(job, queue, tracker, zip_service)
    except asyncio.CancelledError:
        logger.info("Batch worker shutting down")
        raise


async def _process_job(job, queue, tracker, zip_service):
    """Process a single batch job end-to-end."""
    job_id = job.id
    total = len(job.items)

    logger.info(f"Processing batch {job_id} ({total} items)")
    queue.update_job_status(job_id, JobStatus.PROCESSING)

    # Publish initial progress
    await tracker.publish_progress(
        ProgressUpdate(
            job_id=job_id,
            processed=0,
            total=total,
            message="Starting batch processing...",
            status="processing",
        )
    )

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0
    total_bytes = 0

    for item in job.items:
        # Check for cancellation
        current_job = queue.get_job_status(job_id)
        if current_job is None or current_job.status == JobStatus.CANCELLED:
            logger.info(f"Batch {job_id} was cancelled, stopping worker")
            return

        try:
            output_path = await _generate_item(item, job, job_output_dir)

            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            total_bytes += file_size

            queue.update_item_status(
                job_id, item.id, JobStatus.COMPLETED, output_path=str(output_path),
            )
            processed += 1

            await tracker.publish_progress(
                ProgressUpdate(
                    job_id=job_id,
                    processed=processed,
                    total=total,
                    current_item=item.file,
                    message=f"Completed: {item.file}",
                    status="processing",
                    total_size=total_bytes,
                )
            )

        except RetryableError as exc:
            queue.update_item_status(
                job_id, item.id, JobStatus.FAILED,
                error=str(exc), is_retryable=True,
            )
            # If item was reset to PENDING by retry logic, re-process later
            if item.status == JobStatus.PENDING:
                logger.info(f"Item {item.id} queued for retry")
            else:
                failed += 1
                await tracker.publish_progress(
                    ProgressUpdate(
                        job_id=job_id,
                        processed=processed,
                        total=total,
                        current_item=item.file,
                        message=f"Failed (retries exhausted): {item.file}",
                        status="processing",
                        error=str(exc),
                        total_size=total_bytes,
                    )
                )

        except Exception as exc:
            logger.error(f"Item {item.id} failed: {exc}")
            queue.update_item_status(
                job_id, item.id, JobStatus.FAILED, error=str(exc),
            )
            failed += 1

            await tracker.publish_progress(
                ProgressUpdate(
                    job_id=job_id,
                    processed=processed,
                    total=total,
                    current_item=item.file,
                    message=f"Error: {item.file} - {exc}",
                    status="processing",
                    error=str(exc),
                    total_size=total_bytes,
                )
            )

    # Job complete — create ZIP and publish final status
    final_status = "completed" if failed < total else "failed"

    queue.update_job_status(
        job_id, JobStatus.COMPLETED if final_status == "completed" else JobStatus.FAILED,
        processed_count=processed, total_size=total_bytes,
    )

    await tracker.publish_progress(
        ProgressUpdate(
            job_id=job_id,
            processed=processed,
            total=total,
            message=f"Batch complete: {processed}/{total} succeeded",
            status=final_status,
            total_size=total_bytes,
        )
    )

    logger.info(f"Batch {job_id} finished: {processed} ok, {failed} failed")


async def _generate_item(item, job, output_dir: Path) -> str:
    """Generate a single coloring page for a batch item.

    Uses WorkbookImageGenerator for AI-first generation with PIL fallback.
    Returns the path to the generated image file.
    """
    from ..workbook.image_gen import WorkbookImageGenerator

    generator = WorkbookImageGenerator()

    # Derive item name from filename (strip extension)
    item_name = Path(item.file).stem

    # Generate the workbook item (returns WorkbookItem with colored/outline/dashed)
    workbook_item = await generator.generate_item(
        name=item_name,
        category="custom",
    )

    # Save the outline image (most useful for coloring books)
    output_path = output_dir / f"{item_name}_coloring.png"

    if workbook_item.outline:
        workbook_item.outline.save(str(output_path))
    elif workbook_item.colored:
        workbook_item.colored.save(str(output_path))
    else:
        raise RuntimeError(f"No image generated for {item.file}")

    return str(output_path)
