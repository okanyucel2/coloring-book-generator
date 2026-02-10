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
from .models import WorkbookModel, SessionLocal, get_db
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

# In-memory stores for binary PDF data and async task handles.
# PDF bytes are large and ephemeral; database stores metadata only.
_pdfs: dict[str, bytes] = {}  # workbook_id -> PDF bytes
_generation_tasks: dict[str, asyncio.Task] = {}


def _workbook_model_to_response(wb: WorkbookModel) -> WorkbookResponse:
    return WorkbookResponse(
        id=wb.id,
        theme=wb.theme,
        title=wb.title,
        subtitle=wb.subtitle,
        age_min=wb.age_min,
        age_max=wb.age_max,
        page_count=wb.page_count,
        items=wb.items_json or [],
        activity_mix=wb.activity_mix_json or {},
        page_size=wb.page_size,
        status=wb.status,
        progress=wb.progress,
        pdf_url=f"/api/v1/workbooks/{wb.id}/download" if wb.status == "ready" else None,
        etsy_listing_id=wb.etsy_listing_id,
        created_at=wb.created_at,
        updated_at=wb.updated_at,
    )


def get_workbook_by_id(db: Session, workbook_id: str) -> Optional[WorkbookModel]:
    """Helper to fetch a workbook by ID. Used by etsy_routes too."""
    return db.query(WorkbookModel).filter(WorkbookModel.id == workbook_id).first()


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
async def list_workbooks(db: Session = Depends(get_db)):
    """List all workbooks."""
    workbooks = db.query(WorkbookModel).all()
    return [_workbook_model_to_response(wb) for wb in workbooks]


@router.post("/workbooks", response_model=WorkbookResponse, status_code=201)
async def create_workbook(body: WorkbookCreate, db: Session = Depends(get_db)):
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

    now = datetime.now(timezone.utc)

    wb = WorkbookModel(
        theme=body.theme,
        title=body.title,
        subtitle=body.subtitle or theme.get_default_subtitle(body.age_min, body.age_max),
        age_min=body.age_min,
        age_max=body.age_max,
        page_count=body.page_count,
        items_json=items,
        activity_mix_json=activity_mix,
        page_size=body.page_size,
        status="draft",
        progress=None,
        etsy_listing_id=None,
        created_at=now,
        updated_at=now,
    )
    db.add(wb)
    db.flush()
    result = _workbook_model_to_response(wb)
    db.commit()

    return result


@router.get("/workbooks/{workbook_id}", response_model=WorkbookResponse)
async def get_workbook(workbook_id: str, db: Session = Depends(get_db)):
    """Get workbook details."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return _workbook_model_to_response(wb)


@router.put("/workbooks/{workbook_id}", response_model=WorkbookResponse)
async def update_workbook(workbook_id: str, body: WorkbookUpdate, db: Session = Depends(get_db)):
    """Update workbook configuration."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb.status == "generating":
        raise HTTPException(status_code=409, detail="Cannot update while generating")

    if body.title is not None:
        wb.title = body.title
    if body.subtitle is not None:
        wb.subtitle = body.subtitle
    if body.age_min is not None:
        wb.age_min = body.age_min
    if body.age_max is not None:
        wb.age_max = body.age_max
    if body.page_count is not None:
        wb.page_count = body.page_count
    if body.items is not None:
        wb.items_json = body.items
    if body.activity_mix is not None:
        wb.activity_mix_json = body.activity_mix
    if body.page_size is not None:
        wb.page_size = body.page_size

    wb.updated_at = datetime.now(timezone.utc)
    # Reset to draft if config changed
    if wb.status == "ready":
        wb.status = "draft"

    db.commit()
    db.refresh(wb)
    return _workbook_model_to_response(wb)


@router.delete("/workbooks/{workbook_id}")
async def delete_workbook(workbook_id: str, db: Session = Depends(get_db)):
    """Delete a workbook."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    # Cancel generation if running
    task = _generation_tasks.pop(workbook_id, None)
    if task and not task.done():
        task.cancel()

    db.delete(wb)
    db.commit()
    _pdfs.pop(workbook_id, None)

    return {"message": "Workbook deleted"}


# --- Generation ---

@router.post("/workbooks/{workbook_id}/generate", response_model=WorkbookStatusResponse)
async def generate_workbook(workbook_id: str, db: Session = Depends(get_db)):
    """Start PDF generation for a workbook (async)."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb.status == "generating":
        raise HTTPException(status_code=409, detail="Generation already in progress")

    wb.status = "generating"
    wb.progress = 0.0
    db.commit()

    # Start async generation
    task = asyncio.create_task(_generate_pdf(workbook_id))
    _generation_tasks[workbook_id] = task

    return WorkbookStatusResponse(
        id=workbook_id, status="generating", progress=0.0,
    )


async def _generate_pdf(workbook_id: str) -> None:
    """Background task: compile workbook to PDF.

    Uses its own DB session since this runs outside the request lifecycle.
    """
    db = SessionLocal()
    try:
        wb = db.query(WorkbookModel).filter(WorkbookModel.id == workbook_id).first()
        if not wb:
            return

        config = WorkbookConfig(
            theme=wb.theme,
            title=wb.title,
            subtitle=wb.subtitle or "",
            age_range=(wb.age_min, wb.age_max),
            page_count=wb.page_count,
            items=wb.items_json or [],
            activity_mix=wb.activity_mix_json or {},
            page_size=wb.page_size,
        )

        gen = WorkbookImageGenerator(ai_enabled=False)
        compiler = WorkbookCompiler(config=config, image_generator=gen)

        wb.progress = 0.1
        db.commit()

        pdf_bytes = await compiler.compile()

        _pdfs[workbook_id] = pdf_bytes
        wb.status = "ready"
        wb.progress = 1.0
        wb.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Workbook {workbook_id} generated: {len(pdf_bytes)} bytes")

    except Exception as e:
        logger.error(f"Workbook {workbook_id} generation failed: {e}")
        # Re-fetch in case the session is in a bad state
        wb = db.query(WorkbookModel).filter(WorkbookModel.id == workbook_id).first()
        if wb:
            wb.status = "failed"
            wb.progress = None
            db.commit()
    finally:
        db.close()
        _generation_tasks.pop(workbook_id, None)


@router.get("/workbooks/{workbook_id}/status", response_model=WorkbookStatusResponse)
async def get_generation_status(workbook_id: str, db: Session = Depends(get_db)):
    """Get workbook generation progress."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    return WorkbookStatusResponse(
        id=workbook_id,
        status=wb.status,
        progress=wb.progress,
    )


@router.get("/workbooks/{workbook_id}/download")
async def download_workbook(workbook_id: str, db: Session = Depends(get_db)):
    """Download generated PDF."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb.status != "ready":
        raise HTTPException(status_code=409, detail="Workbook not yet generated")

    pdf_bytes = _pdfs.get(workbook_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF not found")

    filename = f"{wb.title.replace(' ', '_')}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/workbooks/{workbook_id}/preview")
async def preview_workbook(workbook_id: str, db: Session = Depends(get_db)):
    """Preview workbook with activity breakdown and page thumbnails data.

    Returns generation status, activity mix breakdown with page ranges,
    and item sampling for each activity type so the frontend can render
    representative thumbnail previews.
    """
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    activity_mix = wb.activity_mix_json or {}
    items = wb.items_json or []
    total_activity_pages = sum(activity_mix.values())

    # Build per-activity breakdown with page ranges and sampled items
    activity_breakdown = []
    current_page = 2  # page 1 is the cover
    for activity_type, count in activity_mix.items():
        if count <= 0:
            continue
        # Sample items that would appear on these pages (cycle through items)
        sampled_items = [items[i % len(items)] for i in range(count)] if items else []
        activity_breakdown.append({
            "activity_type": activity_type,
            "page_count": count,
            "page_range": {"start": current_page, "end": current_page + count - 1},
            "sampled_items": sampled_items[:5],  # cap preview samples at 5
        })
        current_page += count

    # Build thumbnail descriptors for first 3 pages
    page_thumbnails = []
    # Page 1: cover
    page_thumbnails.append({
        "page": 1,
        "type": "cover",
        "label": wb.title,
        "description": f"Cover page - {wb.theme} theme",
    })
    # Pages 2-4: first activities
    thumb_page = 2
    for activity_type, count in activity_mix.items():
        if count <= 0:
            continue
        for i in range(count):
            if thumb_page > 4:
                break
            item = items[(thumb_page - 2) % len(items)] if items else "unknown"
            page_thumbnails.append({
                "page": thumb_page,
                "type": activity_type,
                "label": item.replace("_", " ").title(),
                "description": f"{activity_type.replace('_', ' ').title()} - {item.replace('_', ' ').title()}",
            })
            thumb_page += 1
        if thumb_page > 4:
            break

    return {
        "id": workbook_id,
        "status": wb.status,
        "title": wb.title,
        "theme": wb.theme,
        "total_pages": total_activity_pages + 1,  # +1 for cover
        "activity_mix": activity_mix,
        "activity_breakdown": activity_breakdown,
        "page_thumbnails": page_thumbnails,
        "item_count": len(items),
    }
