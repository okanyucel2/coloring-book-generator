"""Etsy integration API routes."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..etsy.client import EtsyClient
from ..etsy.listing import EtsyListingService
from ..etsy.seo import EtsySEOEngine
from ..workbook.models import WorkbookConfig
from .workbook_routes import _pdfs, _workbooks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etsy", tags=["etsy"])

# Etsy client instance (configured via env vars)
_etsy_client: Optional[EtsyClient] = None
_etsy_state: Optional[str] = None  # OAuth state parameter


def _get_etsy_client() -> EtsyClient:
    global _etsy_client
    if _etsy_client is None:
        api_key = os.environ.get("ETSY_API_KEY", "")
        api_secret = os.environ.get("ETSY_API_SECRET", "")
        redirect_uri = os.environ.get(
            "ETSY_REDIRECT_URI", "http://localhost:5000/api/v1/etsy/callback"
        )
        _etsy_client = EtsyClient(
            api_key=api_key, api_secret=api_secret, redirect_uri=redirect_uri,
        )
    return _etsy_client


# --- Schemas ---

class EtsyAuthURLResponse(BaseModel):
    auth_url: str
    state: str


class EtsyCallbackRequest(BaseModel):
    code: str
    state: str


class EtsyStatusResponse(BaseModel):
    connected: bool
    shop_id: Optional[int] = None


class PublishRequest(BaseModel):
    price_override: Optional[float] = None
    shop_id: int


class PublishResponse(BaseModel):
    listing_id: int
    title: str
    state: str
    price: float


class ListingPreviewResponse(BaseModel):
    title: str
    description: str
    price: float
    tags: list[str]


# --- Routes ---

@router.get("/auth-url", response_model=EtsyAuthURLResponse)
async def get_auth_url():
    """Get OAuth authorization URL."""
    client = _get_etsy_client()
    if not client.api_key:
        raise HTTPException(
            status_code=503,
            detail="Etsy API key not configured. Set ETSY_API_KEY env var.",
        )

    global _etsy_state
    url, state = client.get_auth_url()
    _etsy_state = state

    return EtsyAuthURLResponse(auth_url=url, state=state)


@router.post("/callback")
async def handle_callback(body: EtsyCallbackRequest):
    """Handle OAuth callback with authorization code."""
    global _etsy_state

    if _etsy_state and body.state != _etsy_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client = _get_etsy_client()
    try:
        tokens = await client.exchange_code(body.code)
        _etsy_state = None
        return {"message": "Connected to Etsy", "token_type": tokens.token_type}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")


@router.get("/status", response_model=EtsyStatusResponse)
async def get_status():
    """Check Etsy connection status."""
    client = _get_etsy_client()
    return EtsyStatusResponse(connected=client.is_authenticated)


@router.post("/disconnect")
async def disconnect():
    """Disconnect from Etsy."""
    client = _get_etsy_client()
    client.disconnect()
    return {"message": "Disconnected from Etsy"}


@router.get(
    "/workbooks/{workbook_id}/listing-preview",
    response_model=ListingPreviewResponse,
)
async def preview_listing(workbook_id: str):
    """Preview auto-generated listing metadata for a workbook."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

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

    seo = EtsySEOEngine()
    return ListingPreviewResponse(
        title=seo.generate_title(config),
        description=seo.generate_description(config),
        price=seo.suggest_price(config),
        tags=seo.generate_tags(config),
    )


@router.post("/workbooks/{workbook_id}/publish", response_model=PublishResponse)
async def publish_workbook(workbook_id: str, body: PublishRequest):
    """Create Etsy listing for a workbook."""
    wb = _workbooks.get(workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb["status"] != "ready":
        raise HTTPException(status_code=409, detail="Workbook must be generated first")

    pdf_bytes = _pdfs.get(workbook_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF not found")

    client = _get_etsy_client()
    if not client.is_authenticated:
        raise HTTPException(status_code=401, detail="Not connected to Etsy")

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

    service = EtsyListingService(client=client, shop_id=body.shop_id)

    try:
        listing = await service.create_listing(
            config=config,
            pdf_bytes=pdf_bytes,
            price_override=body.price_override,
        )

        # Store listing ID on workbook
        wb["etsy_listing_id"] = str(listing.listing_id)

        return PublishResponse(
            listing_id=listing.listing_id,
            title=listing.title,
            state=listing.state,
            price=listing.price,
        )
    except Exception as e:
        logger.error(f"Etsy publish failed: {e}")
        raise HTTPException(status_code=502, detail=f"Etsy publish failed: {e}")
