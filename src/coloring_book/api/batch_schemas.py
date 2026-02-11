"""Pydantic schemas for batch generation API endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class BatchItemInput(BaseModel):
    """Single item in a batch submission."""
    file: str
    prompt: str


class BatchOptions(BaseModel):
    """Configuration options for batch processing."""
    quality: str = "standard"
    include_pdf: bool = False


class BatchSubmitRequest(BaseModel):
    """Request body for submitting a batch generation job."""
    items: list[BatchItemInput] = Field(..., min_length=1, max_length=50)
    model: str = "claude"
    options: BatchOptions = BatchOptions()


class BatchSubmitResponse(BaseModel):
    """Response after submitting a batch job."""
    batch_id: str
    status: str
    total_items: int


class BatchProgressResponse(BaseModel):
    """Polling response for batch progress."""
    job_id: str
    status: str
    total_items: int
    processed: int
    failed: int
    pending: int
    progress_percent: int
    total_size_bytes: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    expires_at: Optional[str] = None


class BatchListItem(BaseModel):
    """Summary of a batch job for listing."""
    id: str
    status: str
    total_items: int
    processed: int
    created_at: Optional[str] = None


class BatchListResponse(BaseModel):
    """Response for listing batch jobs."""
    batches: list[dict]
    count: int
