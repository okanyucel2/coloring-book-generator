"""Etsy integration API routes.

OAuth flow: Frontend opens popup → Etsy auth → GET callback → HTML postMessage → popup closes.
Tokens: Encrypted in DB via DbProviderTokenManager (survive restarts).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..etsy.client import (
    EtsyAuthError,
    EtsyClient,
    EtsyConfigError,
    EtsyRateLimitError,
    TokenResponse,
)
from ..etsy.listing import EtsyListingService
from ..etsy.seo import EtsySEOEngine
from ..pdf.auditor import PDFQualityError
from ..workbook.compiler import WorkbookCompiler
from ..workbook.image_gen import WorkbookImageGenerator
from ..workbook.models import WorkbookConfig
from .models import get_db
from .workbook_routes import _pdfs, get_workbook_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etsy", tags=["etsy"])

# Pending OAuth states: state_value → (timestamp, code_verifier)
# Cleaned up on each auth-url request (entries older than 10 min)
_pending_states: dict[str, tuple[float, str]] = {}
_STATE_TTL = 600  # 10 minutes


def _cleanup_expired_states() -> None:
    """Remove states older than _STATE_TTL."""
    now = time.time()
    expired = [s for s, (ts, _) in _pending_states.items() if now - ts > _STATE_TTL]
    for s in expired:
        del _pending_states[s]


def _get_etsy_client() -> EtsyClient:
    """Create an Etsy client from env vars (stateless — tokens come from DB)."""
    api_key = os.environ.get("ETSY_API_KEY", "")
    api_secret = os.environ.get("ETSY_API_SECRET", "")
    redirect_uri = os.environ.get(
        "ETSY_REDIRECT_URI", "http://localhost:5000/api/v1/etsy/callback"
    )
    return EtsyClient(
        api_key=api_key, api_secret=api_secret, redirect_uri=redirect_uri,
    )


def _get_provider_token_manager():
    """Import and return the provider token manager from app module."""
    from .app import get_provider_token_manager
    return get_provider_token_manager()


# User ID for single-user Etsy token storage
def _get_default_user_id() -> str:
    from .app import DEFAULT_USER_ID
    return DEFAULT_USER_ID


# --- Schemas ---

class EtsyAuthURLResponse(BaseModel):
    auth_url: str
    state: str


class EtsyStatusResponse(BaseModel):
    connected: bool
    shop_id: Optional[int] = None
    shop_name: Optional[str] = None
    api_key_configured: bool = False


class PublishRequest(BaseModel):
    price_override: Optional[float] = None
    shop_id: Optional[int] = None  # Optional now — auto-fetched from DB if omitted


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


class BatchPublishRequest(BaseModel):
    workbook_ids: list[str]
    price_override: Optional[float] = None


class BatchItemResult(BaseModel):
    workbook_id: str
    status: str  # "success" | "error" | "skipped"
    listing_id: Optional[int] = None
    title: Optional[str] = None
    error: Optional[str] = None


class BatchPublishResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[BatchItemResult]


# --- Routes ---

@router.get("/auth-url", response_model=EtsyAuthURLResponse)
async def get_auth_url():
    """Get OAuth authorization URL.

    Returns a URL for the user to visit to authorize the application.
    Requires ETSY_API_KEY to be set in environment variables.
    """
    _cleanup_expired_states()

    client = _get_etsy_client()

    try:
        url, state = client.get_auth_url()
    except EtsyConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Store state with timestamp and code_verifier for callback validation
    _pending_states[state] = (time.time(), client._code_verifier or "")
    return EtsyAuthURLResponse(auth_url=url, state=state)


@router.get("/callback")
async def handle_callback(
    code: str = Query(..., description="Authorization code from Etsy"),
    state: str = Query(..., description="OAuth state parameter"),
):
    """Handle OAuth callback from Etsy (GET redirect).

    Exchanges the authorization code for tokens, stores them encrypted in DB,
    fetches shop info via get_me(), then returns an HTML page that signals the
    opener window via postMessage and closes itself.
    """
    # Validate state
    if state not in _pending_states:
        return HTMLResponse(content=_oauth_error_html(
            "Invalid or expired OAuth state. Please try connecting again."
        ))

    timestamp, code_verifier = _pending_states.pop(state)

    if time.time() - timestamp > _STATE_TTL:
        return HTMLResponse(content=_oauth_error_html(
            "OAuth session expired. Please try connecting again."
        ))

    # Create client and restore PKCE verifier
    client = _get_etsy_client()
    client._code_verifier = code_verifier

    try:
        tokens = await client.exchange_code(code)
    except EtsyConfigError as e:
        return HTMLResponse(content=_oauth_error_html(str(e)))
    except EtsyAuthError as e:
        return HTMLResponse(content=_oauth_error_html(str(e)))
    except EtsyRateLimitError:
        return HTMLResponse(content=_oauth_error_html(
            "Etsy rate limit hit. Please wait a moment and try again."
        ))
    except Exception as e:
        logger.error(f"Unexpected OAuth error: {e}", exc_info=True)
        return HTMLResponse(content=_oauth_error_html(
            "An unexpected error occurred. Please try again."
        ))

    # Fetch shop info
    shop_id = None
    shop_name = None
    try:
        me = await client.get_me()
        shop_id = me.get("shop_id")
        shop_name = me.get("shop_name", "")
    except Exception as e:
        logger.warning(f"Could not fetch Etsy user info: {e}")

    # Store tokens in DB
    try:
        ptm = _get_provider_token_manager()
        user_id = _get_default_user_id()
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)

        await ptm.store_tokens(
            user_id=user_id,
            provider="etsy",
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            scopes={"scopes": ["listings_w", "listings_r", "shops_r"]},
            expires_at=expires_at,
            provider_metadata={
                "shop_id": shop_id,
                "shop_name": shop_name,
            },
        )
    except HTTPException:
        # Token manager not available — fall back to success without persistence
        logger.warning("Provider token manager not available — tokens not persisted to DB")
    except Exception as e:
        logger.error(f"Failed to store Etsy tokens: {e}", exc_info=True)

    return HTMLResponse(content=_oauth_success_html(shop_id=shop_id, shop_name=shop_name))


@router.get("/status", response_model=EtsyStatusResponse)
async def get_status():
    """Check Etsy connection status from DB."""
    client = _get_etsy_client()
    api_key_configured = bool(client.api_key)

    try:
        ptm = _get_provider_token_manager()
        user_id = _get_default_user_id()
        tokens = await ptm.get_tokens(user_id, "etsy")
        if tokens:
            metadata = tokens.provider_metadata or {}
            return EtsyStatusResponse(
                connected=True,
                shop_id=metadata.get("shop_id"),
                shop_name=metadata.get("shop_name"),
                api_key_configured=api_key_configured,
            )
    except HTTPException:
        pass  # Token manager not available
    except Exception as e:
        logger.warning(f"Error checking Etsy status: {e}")

    return EtsyStatusResponse(
        connected=False,
        api_key_configured=api_key_configured,
    )


@router.post("/disconnect")
async def disconnect():
    """Disconnect from Etsy by removing stored tokens from DB."""
    try:
        ptm = _get_provider_token_manager()
        user_id = _get_default_user_id()
        deleted = await ptm.delete_tokens(user_id, "etsy")
        if deleted:
            return {"message": "Disconnected from Etsy"}
        return {"message": "No Etsy connection found"}
    except HTTPException:
        return {"message": "Disconnected from Etsy"}


@router.get(
    "/workbooks/{workbook_id}/listing-preview",
    response_model=ListingPreviewResponse,
)
async def preview_listing(workbook_id: str, db: AsyncSession = Depends(get_db)):
    """Preview auto-generated listing metadata for a workbook."""
    wb = await get_workbook_by_id(db, workbook_id)
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
async def publish_workbook(workbook_id: str, body: PublishRequest, db: AsyncSession = Depends(get_db)):
    """Create Etsy listing for a workbook.

    Loads tokens from DB, auto-refreshes if expired, fetches shop_id from
    provider_metadata if not provided in request.
    """
    wb = await get_workbook_by_id(db, workbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Workbook not found")

    if wb.status != "ready":
        raise HTTPException(status_code=409, detail="Workbook must be generated first")

    if wb.status != "ready" and not _pdfs.get(workbook_id):
        raise HTTPException(status_code=404, detail="PDF not found — workbook not generated")

    # Authenticate
    client, shop_id_from_db = await _get_authenticated_client()

    # Use request shop_id or fall back to DB
    shop_id = body.shop_id or shop_id_from_db

    # Re-compile with etsy_standard profile (300 DPI, grayscale, compressed)
    try:
        pdf_bytes = await _compile_for_etsy(wb)
    except PDFQualityError as e:
        raise HTTPException(
            status_code=422,
            detail=f"PDF quality check failed for Etsy: {'; '.join(e.issues)}",
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

    service = EtsyListingService(client=client, shop_id=shop_id)

    try:
        listing = await service.create_listing(
            config=config,
            pdf_bytes=pdf_bytes,
            price_override=body.price_override,
        )

        wb.etsy_listing_id = str(listing.listing_id)
        await db.commit()

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


# --- Shared Helpers ---

async def _get_authenticated_client() -> tuple[EtsyClient, int]:
    """Load tokens from DB, refresh if expired, return (client, shop_id).

    Raises HTTPException on auth failure.
    """
    client = _get_etsy_client()

    if not client.api_key:
        raise HTTPException(
            status_code=503,
            detail="Etsy API key is not configured.",
        )

    try:
        ptm = _get_provider_token_manager()
        user_id = _get_default_user_id()

        async def _refresh_fn(refresh_token: str) -> dict:
            temp_client = _get_etsy_client()
            temp_client.tokens = TokenResponse(
                access_token="expired",
                refresh_token=refresh_token,
            )
            new_tokens = await temp_client.refresh_token()
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens.expires_in)
            return {
                "access_token": new_tokens.access_token,
                "refresh_token": new_tokens.refresh_token,
                "expires_at": expires_at,
            }

        token_data = await ptm.refresh_if_expired(user_id, "etsy", _refresh_fn)

        client.tokens = TokenResponse(
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token or "",
        )

        shop_id = None
        if token_data.provider_metadata:
            shop_id = token_data.provider_metadata.get("shop_id")

        if not shop_id:
            raise HTTPException(status_code=400, detail="No shop_id available. Please reconnect to Etsy.")

        return client, shop_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to load Etsy tokens: {e}")


@router.post("/workbooks/batch-publish", response_model=BatchPublishResponse)
async def batch_publish_workbooks(
    body: BatchPublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """Publish multiple workbooks to Etsy in one request.

    Authenticates once, then publishes each workbook sequentially
    (respecting Etsy rate limits). Returns per-item results so
    partial failures don't block the entire batch.
    """
    if not body.workbook_ids:
        raise HTTPException(status_code=400, detail="workbook_ids cannot be empty")

    if len(body.workbook_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 workbooks per batch")

    # Authenticate once for the whole batch
    client, shop_id = await _get_authenticated_client()

    results: list[BatchItemResult] = []
    succeeded = 0
    failed = 0
    skipped = 0

    for wb_id in body.workbook_ids:
        # Fetch workbook
        wb = await get_workbook_by_id(db, wb_id)
        if not wb:
            results.append(BatchItemResult(
                workbook_id=wb_id, status="skipped", error="Workbook not found",
            ))
            skipped += 1
            continue

        if wb.status != "ready":
            results.append(BatchItemResult(
                workbook_id=wb_id, status="skipped", error="Workbook not ready (not generated yet)",
            ))
            skipped += 1
            continue

        if wb.etsy_listing_id:
            results.append(BatchItemResult(
                workbook_id=wb_id, status="skipped",
                error=f"Already published (listing {wb.etsy_listing_id})",
            ))
            skipped += 1
            continue

        # Check that workbook has been generated (home PDF exists or status is ready)
        if not _pdfs.get(wb_id) and wb.status != "ready":
            results.append(BatchItemResult(
                workbook_id=wb_id, status="skipped", error="PDF not found",
            ))
            skipped += 1
            continue

        # Re-compile with etsy_standard profile (300 DPI, grayscale)
        try:
            pdf_bytes = await _compile_for_etsy(wb)
        except PDFQualityError as e:
            results.append(BatchItemResult(
                workbook_id=wb_id, status="error",
                error=f"PDF quality check failed: {'; '.join(e.issues)}",
            ))
            failed += 1
            continue
        except Exception as e:
            results.append(BatchItemResult(
                workbook_id=wb_id, status="error",
                error=f"Failed to compile PDF: {e}",
            ))
            failed += 1
            continue

        # Build config and publish
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

        service = EtsyListingService(client=client, shop_id=shop_id)

        try:
            listing = await service.create_listing(
                config=config,
                pdf_bytes=pdf_bytes,
                price_override=body.price_override,
            )
            wb.etsy_listing_id = str(listing.listing_id)
            await db.commit()

            results.append(BatchItemResult(
                workbook_id=wb_id,
                status="success",
                listing_id=listing.listing_id,
                title=listing.title,
            ))
            succeeded += 1

        except EtsyRateLimitError as e:
            # Stop the batch on rate limit — remaining items would also fail
            results.append(BatchItemResult(
                workbook_id=wb_id, status="error",
                error=f"Rate limited (retry after {e.retry_after}s). Batch stopped.",
            ))
            failed += 1
            # Mark remaining as skipped
            remaining = body.workbook_ids[body.workbook_ids.index(wb_id) + 1:]
            for rem_id in remaining:
                results.append(BatchItemResult(
                    workbook_id=rem_id, status="skipped",
                    error="Skipped due to rate limit on earlier item",
                ))
                skipped += 1
            break

        except Exception as e:
            logger.error(f"Batch publish failed for {wb_id}: {e}", exc_info=True)
            results.append(BatchItemResult(
                workbook_id=wb_id, status="error", error=str(e),
            ))
            failed += 1

    return BatchPublishResponse(
        total=len(body.workbook_ids),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
    )


async def _compile_for_etsy(wb) -> bytes:
    """Re-compile workbook with etsy_standard profile (300 DPI, grayscale, compressed).

    Returns PDF bytes optimized for Etsy digital download (under 20MB).
    """
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
    result = await compiler.compile(profile="etsy_standard")
    return result.pdf_bytes


# --- HTML Response Helpers ---

def _oauth_success_html(shop_id: int | None = None, shop_name: str | None = None) -> str:
    """HTML page that signals OAuth success to opener via postMessage."""
    shop_id_js = str(shop_id) if shop_id else "null"
    shop_name_js = f'"{shop_name}"' if shop_name else "null"
    return f"""<!DOCTYPE html>
<html><head><title>Etsy Connected</title></head>
<body>
<p>Connected to Etsy! This window will close automatically.</p>
<script>
if (window.opener) {{
    window.opener.postMessage({{
        type: "etsy-oauth-complete",
        success: true,
        shopId: {shop_id_js},
        shopName: {shop_name_js}
    }}, "*");
}}
setTimeout(function() {{ window.close(); }}, 1500);
</script>
</body></html>"""


def _oauth_error_html(message: str) -> str:
    """HTML page that signals OAuth failure to opener via postMessage."""
    # Escape message for JS string
    safe_message = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f"""<!DOCTYPE html>
<html><head><title>Etsy Connection Failed</title></head>
<body>
<p>Connection failed: {message}</p>
<p>You can close this window and try again.</p>
<script>
if (window.opener) {{
    window.opener.postMessage({{
        type: "etsy-oauth-complete",
        success: false,
        error: "{safe_message}"
    }}, "*");
}}
</script>
</body></html>"""
