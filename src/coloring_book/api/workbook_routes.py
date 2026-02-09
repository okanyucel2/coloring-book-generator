"""Workbook API routes - CRUD + generation + download."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..workbook.compiler import WorkbookCompiler
from ..workbook.image_gen import WorkbookImageGenerator
from ..workbook.models import DEFAULT_ACTIVITY_MIX, WorkbookConfig
from ..workbook.themes import THEMES, get_theme, list_themes
from .models import get_db
from .workbook_schemas import (
    ThemeListResponse,
    ThemeResponse,
    WorkbookCreate,
    WorkbookResponse,
    WorkbookStatusResponse,
    WorkbookUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["workbooks"])

# In-memory store for workbooks (will be replaced with DB model)
# Using dict for simplicity - production would use SQLAlchemy model
_workbooks: dict[str, dict] = {}
_pdfs: dict[str, bytes] = {}  # workbook_id -> PDF bytes
_generation_tasks: dict[str, asyncio.Task] = {}


def _workbook_to_response(wb: dict) -> WorkbookResponse:
    return WorkbookResponse(
        id=wb["id"],
        theme=wb["theme"],
        title=wb["title"],
        subtitle=wb.get("subtitle"),
        age_min=wb["age_min"],
        age_max=wb["age_max"],
        page_count=wb["page_count"],
        items=wb["items"],
        activity_mix=wb["activity_mix"],
        page_size=wb["page_size"],
        status=wb["status"],
        progress=wb.get("progress"),
        pdf_url=f"/api/v1/workbooks/{wb['id']}/download" if wb["status"] == "ready" else None,
        etsy_listing_id=wb.get("etsy_listing_id"),
        created_at=wb.get("created_at"),
        updated_at=wb.get("updated_at"),
    )


# --- Theme endpoints ---

@router.get("/themes", response_model=ThemeListResponse)
async def get_themes():
    """List all available themes."""
    themes = list_themes()
    return ThemeListResponse(
        data=[
            ThemeResponse(
                slug=t.slug,
                display_name=t.display_name,
                category=t.category,
                items=t.items,
                item_count=t.item_count,
                age_groups=t.age_groups,
                etsy_tags=t.etsy_tags,
            )
            for t in themes
        ]
    )


@router.get("/themes/{slug}", response_model=ThemeResponse)
async def get_theme_detail(slug: str):
    """Get theme details by slug."""
    try:
        t = get_theme(slug)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Theme '{slug}' not found")

    return ThemeResponse(
        slug=t.slug,
        display_name=t.display_name,
        category=t.category,
        items=t.items,
        item_count=t.item_count,
        age_groups=t.age_groups,
        etsy_tags=t.etsy_tags,
    )


# --- Workbook CRUD ---

@router.get("/workbooks", response_model=list[WorkbookResponse])
async def list_workbooks():
    """List all workbooks."""
    return [_workbook_to_response(wb) for wb in _workbooks.values()]


@router.post("/workbooks", response_model=WorkbookResponse, status_code=201)
async def create_workbook(body: WorkbookCreate):
    """Create a new workbook configuration."""
    # Validate theme exists
    try:
        theme = get_theme(body.theme)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown theme: {body.theme}")

    # Validate age range
    if body.age_min > body.age_max:
        raise HTTPException(status_code=400, detail="age_min must be <= age_max")

    # Resolve items
    items = body.items if body.items else theme.items
    activity_mix = body.activity_mix if body.activity_mix else dict(DEFAULT_ACTIVITY_MIX)

    wb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    wb = {
        "id": wb_id,
        "theme": body.theme,
        "title": body.title,
        "subtitle": body.subtitle or theme.get_default_subtitle(body.age_min, body.age_max),
        "age_min": body.age_min,
        "age_max": body.age_max,
        "page_count": body.page_count,
        "items": items,
        "activity_mix": activity_mix,
        "page_size": body.page_size,
        "status": "draft",
        "progress": None,
        "etsy_listing_id": None,
        "created_at": now,
        "updated_at": now,
    }
    _workbooks[wb_id] = wb

    return _workbook_to_response(wb)


@router.get("/workbooks/{workbook_id}", response_model=WorkbookResponse)
async def get_workbook(workbook_id: str):
    """Get workbook details."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return _workbook_to_response(wb)


@router.put("/workbooks/{workbook_id}", response_model=WorkbookResponse)
async def update_workbook(workbook_id: str, body: WorkbookUpdate):
    """Update workbook configuration."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb["status"] == "generating":
        raise HTTPException(status_code=409, detail="Cannot update while generating")

    if body.title is not None:
        wb["title"] = body.title
    if body.subtitle is not None:
        wb["subtitle"] = body.subtitle
    if body.age_min is not None:
        wb["age_min"] = body.age_min
    if body.age_max is not None:
        wb["age_max"] = body.age_max
    if body.page_count is not None:
        wb["page_count"] = body.page_count
    if body.items is not None:
        wb["items"] = body.items
    if body.activity_mix is not None:
        wb["activity_mix"] = body.activity_mix
    if body.page_size is not None:
        wb["page_size"] = body.page_size

    wb["updated_at"] = datetime.now(timezone.utc)
    # Reset to draft if config changed
    if wb["status"] == "ready":
        wb["status"] = "draft"

    return _workbook_to_response(wb)


@router.delete("/workbooks/{workbook_id}")
async def delete_workbook(workbook_id: str):
    """Delete a workbook."""
    if workbook_id not in _workbooks:
        raise HTTPException(status_code=404, detail="Workbook not found")

    # Cancel generation if running
    task = _generation_tasks.pop(workbook_id, None)
    if task and not task.done():
        task.cancel()

    del _workbooks[workbook_id]
    _pdfs.pop(workbook_id, None)

    return {"message": "Workbook deleted"}


# --- Generation ---

@router.post("/workbooks/{workbook_id}/generate", response_model=WorkbookStatusResponse)
async def generate_workbook(workbook_id: str):
    """Start PDF generation for a workbook (async)."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb["status"] == "generating":
        raise HTTPException(status_code=409, detail="Generation already in progress")

    wb["status"] = "generating"
    wb["progress"] = 0.0

    # Start async generation
    task = asyncio.create_task(_generate_pdf(workbook_id))
    _generation_tasks[workbook_id] = task

    return WorkbookStatusResponse(
        id=workbook_id, status="generating", progress=0.0,
    )


async def _generate_pdf(workbook_id: str) -> None:
    """Background task: compile workbook to PDF."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        return

    try:
        config = WorkbookConfig(
            theme=wb["theme"],
            title=wb["title"],
            subtitle=wb.get("subtitle", ""),
            age_range=(wb["age_min"], wb["age_max"]),
            page_count=wb["page_count"],
            items=wb["items"],
            activity_mix=wb["activity_mix"],
            page_size=wb["page_size"],
        )

        gen = WorkbookImageGenerator(ai_enabled=False)
        compiler = WorkbookCompiler(config=config, image_generator=gen)

        wb["progress"] = 0.1
        pdf_bytes = await compiler.compile()

        _pdfs[workbook_id] = pdf_bytes
        wb["status"] = "ready"
        wb["progress"] = 1.0
        wb["updated_at"] = datetime.now(timezone.utc)

        logger.info(f"Workbook {workbook_id} generated: {len(pdf_bytes)} bytes")

    except Exception as e:
        logger.error(f"Workbook {workbook_id} generation failed: {e}")
        wb["status"] = "failed"
        wb["progress"] = None
    finally:
        _generation_tasks.pop(workbook_id, None)


@router.get("/workbooks/{workbook_id}/status", response_model=WorkbookStatusResponse)
async def get_generation_status(workbook_id: str):
    """Get workbook generation progress."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    return WorkbookStatusResponse(
        id=workbook_id,
        status=wb["status"],
        progress=wb.get("progress"),
    )


@router.get("/workbooks/{workbook_id}/download")
async def download_workbook(workbook_id: str):
    """Download generated PDF."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb["status"] != "ready":
        raise HTTPException(status_code=409, detail="Workbook not yet generated")

    pdf_bytes = _pdfs.get(workbook_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF not found")

    filename = f"{wb['title'].replace(' ', '_')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/workbooks/{workbook_id}/preview")
async def preview_workbook(workbook_id: str):
    """Preview first 3 pages (returns generation status + page count)."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    return {
        "id": workbook_id,
        "status": wb["status"],
        "title": wb["title"],
        "theme": wb["theme"],
        "total_pages": sum(wb["activity_mix"].values()) + 1,  # +1 for cover
        "activity_mix": wb["activity_mix"],
    }
