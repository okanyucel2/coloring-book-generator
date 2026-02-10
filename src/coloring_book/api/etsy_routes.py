"""Etsy integration API routes."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..etsy.client import (
    EtsyAuthError,
    EtsyClient,
    EtsyConfigError,
    EtsyRateLimitError,
)
from ..etsy.listing import EtsyListingService
from ..etsy.seo import EtsySEOEngine
from ..workbook.models import WorkbookConfig
from .models import get_db
from .workbook_routes import _pdfs, get_workbook_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etsy", tags=["etsy"])

# Etsy client instance (configured via env vars)
_etsy_client: Optional[EtsyClient] = None
_etsy_state: Optional[str] = None  # OAuth state parameter


def _get_etsy_client() -> EtsyClient:
    """Get or create the Etsy client singleton.

    Returns:
        EtsyClient instance (may have empty credentials until auth-url is called)
    """
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
    api_key_configured: bool = False


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
    """Get OAuth authorization URL.

    Returns a URL for the user to visit to authorize the application.
    Requires ETSY_API_KEY to be set in environment variables.
    """
    client = _get_etsy_client()

    try:
        url, state = client.get_auth_url()
    except EtsyConfigError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    global _etsy_state
    _etsy_state = state
    return EtsyAuthURLResponse(auth_url=url, state=state)


@router.post("/callback")
async def handle_callback(body: EtsyCallbackRequest):
    """Handle OAuth callback with authorization code.

    Exchanges the authorization code for access and refresh tokens.
    """
    global _etsy_state

    if _etsy_state and body.state != _etsy_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state parameter. The authorization request may have "
                   "expired or been tampered with. Please start the OAuth flow again.",
        )

    client = _get_etsy_client()
    try:
        tokens = await client.exchange_code(body.code)
        _etsy_state = None
        return {"message": "Connected to Etsy", "token_type": tokens.token_type}
    except EtsyConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except EtsyAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EtsyRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))} if e.retry_after else None,
        )
    except Exception as e:
        logger.error(f"Unexpected OAuth error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during Etsy authentication. "
                   "Please try again or check the server logs.",
        )


@router.get("/status", response_model=EtsyStatusResponse)
async def get_status():
    """Check Etsy connection status.

    Returns whether the client is authenticated and whether the API key is configured.
    """
    client = _get_etsy_client()
    return EtsyStatusResponse(
        connected=client.is_authenticated,
        api_key_configured=bool(client.api_key),
    )


@router.post("/disconnect")
async def disconnect():
    """Disconnect from Etsy by clearing stored tokens."""
    client = _get_etsy_client()
    client.disconnect()
    return {"message": "Disconnected from Etsy"}


@router.get(
    "/workbooks/{workbook_id}/listing-preview",
    response_model=ListingPreviewResponse,
)
async def preview_listing(workbook_id: str, db: Session = Depends(get_db)):
    """Preview auto-generated listing metadata for a workbook."""
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

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

    seo = EtsySEOEngine()
    return ListingPreviewResponse(
        title=seo.generate_title(config),
        description=seo.generate_description(config),
        price=seo.suggest_price(config),
        tags=seo.generate_tags(config),
    )


@router.post("/workbooks/{workbook_id}/publish", response_model=PublishResponse)
async def publish_workbook(workbook_id: str, body: PublishRequest, db: Session = Depends(get_db)):
    """Create Etsy listing for a workbook.

    Requires the workbook to be generated (status=ready) and an active
    Etsy connection.
    """
    wb = get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb.status != "ready":
        raise HTTPException(status_code=409, detail="Workbook must be generated first")

    pdf_bytes = _pdfs.get(workbook_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF not found")

    client = _get_etsy_client()

    # Check configuration before attempting publish
    if not client.api_key:
        raise HTTPException(
            status_code=503,
            detail="Etsy API key is not configured. "
                   "Set the ETSY_API_KEY environment variable.",
        )

    if not client.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Etsy. "
                   "Please complete the OAuth flow first via /api/v1/etsy/auth-url.",
        )

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

    service = EtsyListingService(client=client, shop_id=body.shop_id)

    try:
        listing = await service.create_listing(
            config=config,
            pdf_bytes=pdf_bytes,
            price_override=body.price_override,
        )

        # Store listing ID on workbook
        wb.etsy_listing_id = str(listing.listing_id)
        db.commit()

        return PublishResponse(
            listing_id=listing.listing_id,
            title=listing.title,
            state=listing.state,
            price=listing.price,
        )
    except EtsyConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except EtsyAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except EtsyRateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))} if e.retry_after else None,
        )
    except Exception as e:
        logger.error(f"Etsy publish failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Etsy publish failed: {e}. "
                   "Check your Etsy connection and try again.",
        )
