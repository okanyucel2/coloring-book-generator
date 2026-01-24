"""
Batch job orchestrator for generating coloring books in bulk.
Manages job queue, progress tracking, and ZIP export.
"""
import json
import uuid
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import threading
import zipfile
import io

from .pipeline import ColoreringBookPipeline


class JobStatus(str, Enum):
    """Batch job status states"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


@dataclass
class BatchJob:
    """Represents a single batch generation job"""
    id: str
    name: str
    status: JobStatus
    total_items: int
    completed_items: int = 0
    failed_items: int = 0
    config: dict = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    output_path: Optional[str] = None

    def to_dict(self):
        """Convert to serializable dict"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @property
    def progress(self) -> float:
        """Progress as decimal 0.0-1.0"""
        if self.total_items == 0:
            return 0.0
        return self.completed_items / self.total_items


class BatchRunner:
    """Orchestrates batch generation of coloring books"""

    def __init__(self, output_dir: str = "output/batches"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.jobs: dict[str, BatchJob] = {}
        self.pipeline = ColoreringBookPipeline()
        self._lock = threading.Lock()

    def create_job(
        self,
        name: str,
        animal_count: int,
        animal_types: Optional[List[str]] = None,
        page_size: str = "A4",
        use_ai: bool = True,
    ) -> BatchJob:
        """Create a new batch job"""
        job_id = str(uuid.uuid4())[:8]
        
        job = BatchJob(
            id=job_id,
            name=name,
            status=JobStatus.PENDING,
            total_items=animal_count,
            config={
                'animal_types': animal_types or [],
                'page_size': page_size,
                'use_ai': use_ai,
            },
            created_at=datetime.utcnow().isoformat(),
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        return job

    def start_job(self, job_id: str) -> bool:
        """Start processing a batch job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow().isoformat()
        
        # Start async processing
        thread = threading.Thread(
            target=self._process_job,
            args=(job_id,),
            daemon=True
        )
        thread.start()
        return True

    def _process_job(self, job_id: str):
        """Process job items (runs in background thread)"""
        job = self.jobs[job_id]
        job_output_dir = self.output_dir / job_id
        job_output_dir.mkdir(exist_ok=True)
        
        try:
            animal_types = job.config.get('animal_types', [])
            
            # Generate items
            for i in range(job.total_items):
                try:
                    # Use AI if animal not in built-in types
                    use_ai = job.config.get('use_ai', True)
                    
                    # Generate book (placeholder for now)
                    book = self.pipeline.generate(
                        animals=animal_types if animal_types else [f"animal_{i}"],
                        use_ai=use_ai,
                    )
                    
                    # Save outputs
                    item_dir = job_output_dir / f"item_{i+1:03d}"
                    item_dir.mkdir(exist_ok=True)
                    
                    # Save PDF
                    pdf_path = item_dir / "coloring_book.pdf"
                    book.save_pdf(str(pdf_path))
                    
                    job.completed_items += 1
                    
                except Exception as e:
                    job.failed_items += 1
                    print(f"Error processing item {i+1}: {e}")
            
            # Create ZIP export
            zip_path = job_output_dir / f"{job_id}.zip"
            self._create_zip_export(job_output_dir, zip_path)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            job.output_path = str(zip_path)
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow().isoformat()

    def _create_zip_export(self, source_dir: Path, zip_path: Path):
        """Create ZIP file from job output"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file() and not file_path.name.endswith('.zip'):
                    arcname = file_path.relative_to(source_dir.parent)
                    zf.write(file_path, arcname)

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def get_jobs(self, status: Optional[JobStatus] = None) -> List[BatchJob]:
        """Get all jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def pause_job(self, job_id: str) -> bool:
        """Pause an active job"""
        if job_id not in self.jobs:
            return False
        job = self.jobs[job_id]
        if job.status == JobStatus.PROCESSING:
            job.status = JobStatus.PAUSED
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        if job_id not in self.jobs:
            return False
        job = self.jobs[job_id]
        if job.status == JobStatus.PAUSED:
            self.start_job(job_id)
            return True
        return False

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its outputs"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        job_dir = self.output_dir / job_id
        
        # Remove output files
        if job_dir.exists():
            import shutil
            shutil.rmtree(job_dir)
        
        del self.jobs[job_id]
        return True
