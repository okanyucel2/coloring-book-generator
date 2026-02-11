"""Coloring Book Generator — FastAPI Backend API"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

# Load project-level .env (override=True so project .env wins over root .env)
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parents[3]  # src/coloring_book/api/app.py → project root
load_dotenv(_project_root / ".env", override=True)
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Base, Prompt, ProviderToken, User, Variation, WorkbookModel, async_session, create_tables, get_db
from .schemas import GenerateRequest, PromptCreate, PromptUpdate, VariationUpdate
from .workbook_routes import router as workbook_router
from .etsy_routes import router as etsy_router
from .batch_router import router as batch_router
from . import batch_router as batch_router_module
from ..services.batch_queue_optimized import BatchQueue
from ..services.progress_tracker_optimized import ProgressTracker
from ..services.zip_export import ZipExportService
from ..services.batch_worker import batch_worker

logger = logging.getLogger(__name__)

# --- Default user ID for single-user flows (Etsy OAuth without Google auth) ---
DEFAULT_USER_ID = "default-system-user"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    # Ensure a default user exists for provider token FK constraint
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
        if not result.scalars().first():
            db.add(User(
                id=DEFAULT_USER_ID,
                email="system@localhost",
                name="System",
                provider="system",
            ))
            await db.commit()

    # --- Batch services startup ---
    _batch_queue = BatchQueue()
    await _batch_queue.start()

    _progress_tracker = ProgressTracker()
    await _progress_tracker.start_cleanup_task()

    _zip_service = ZipExportService(temp_dir=os.path.join(tempfile.gettempdir(), "coloring_book_zip"))

    # Inject singletons into the batch router module
    batch_router_module.batch_queue = _batch_queue
    batch_router_module.progress_tracker = _progress_tracker
    batch_router_module.zip_service = _zip_service

    # Start background worker
    worker_task = asyncio.create_task(
        batch_worker(_batch_queue, _progress_tracker, _zip_service)
    )
    logger.info("Batch services initialized (queue + tracker + worker)")

    yield

    # --- Batch services shutdown ---
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await _batch_queue.stop()
    await _progress_tracker.shutdown()
    logger.info("Batch services shut down")

app = FastAPI(title="Coloring Book API", version="0.1.0", lifespan=lifespan)

# --- Provider Token Manager (encrypted token storage, needed for Etsy even without Google auth) ---
_provider_token_manager = None
try:
    from auth_core.encryption import TokenEncryption
    from .provider_token_service import DbProviderTokenManager

    _provider_key = os.environ.get("PROVIDER_TOKEN_KEY", "")
    if not _provider_key:
        _provider_key = TokenEncryption.generate_key()
        logger.warning("PROVIDER_TOKEN_KEY not set — using auto-generated key (dev only, tokens lost on restart)")
    _token_encryption = TokenEncryption(_provider_key)
    _provider_token_manager = DbProviderTokenManager(
        encryption=_token_encryption,
        session_factory=async_session,
    )
    logger.info("Provider token manager initialized (Etsy/provider token storage active)")
except ImportError:
    logger.warning("auth-core not installed — provider token manager disabled (Etsy tokens will be in-memory only)")

# --- Google Auth integration (conditional — requires JWT_SECRET + Google OAuth env vars) ---
_jwt_secret = os.environ.get("JWT_SECRET", "")
_google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
_google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

if _jwt_secret and len(_jwt_secret) >= 32 and _google_client_id and _google_client_secret:
    try:
        from starlette.middleware.sessions import SessionMiddleware
        from auth_fastapi import AuthConfig, create_auth_router, register_auth_exception_handlers

        _auth_config = AuthConfig(
            google_client_id=_google_client_id,
            google_client_secret=_google_client_secret,
            jwt_secret=_jwt_secret,
            frontend_url=os.environ.get("FRONTEND_URL", "http://localhost:5173"),
            backend_url=os.environ.get("BACKEND_URL", None),
        )

        # SessionMiddleware must be added BEFORE CORSMiddleware so CORS ends up outermost
        # (Starlette processes middleware in LIFO order — last added = outermost)
        app.add_middleware(SessionMiddleware, secret_key=_auth_config.effective_session_secret)
        register_auth_exception_handlers(app)

        auth_router = create_auth_router(
            _auth_config, User, get_db,
            token_encryption=_token_encryption if _provider_token_manager else None,
        )
        app.include_router(auth_router, prefix="/auth")
        logger.info("Auth router mounted at /auth")
    except ImportError:
        logger.warning("Auth packages not installed (genesis-auth-core/auth-fastapi) — auth disabled")
else:
    logger.info("Google auth not configured (missing JWT_SECRET/GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)")

# CORS must be added LAST so it's the outermost middleware and handles preflight OPTIONS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_provider_token_manager():
    """FastAPI dependency that returns the DbProviderTokenManager instance."""
    if _provider_token_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Provider token manager not configured (auth-core package not installed)",
        )
    return _provider_token_manager


# Mount workbook, Etsy, and batch routes
app.include_router(workbook_router)
app.include_router(etsy_router)
app.include_router(batch_router)


def _prompt_to_dict(p: Prompt) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "promptText": p.prompt_text,
        "category": p.category,
        "tags": p.tags or [],
        "isPublic": p.is_public,
        "rating": p.rating,
        "usageCount": p.usage_count,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


def _variation_to_dict(v: Variation) -> dict:
    return {
        "id": v.id,
        "prompt": v.prompt,
        "model": v.model,
        "imageUrl": v.image_url,
        "rating": v.rating,
        "seed": v.seed,
        "notes": v.notes,
        "parameters": v.parameters or {},
        "generatedAt": v.generated_at.isoformat() if v.generated_at else None,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Prompt Library ---

@app.get("/api/v1/prompts/library")
async def list_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return {"data": [_prompt_to_dict(p) for p in prompts]}


@app.post("/api/v1/prompts/library", status_code=201)
async def create_prompt(body: PromptCreate, db: AsyncSession = Depends(get_db)):
    prompt = Prompt(
        name=body.name,
        prompt_text=body.promptText,
        category=body.category,
        tags=body.tags,
        is_public=body.isPublic,
    )
    db.add(prompt)
    await db.flush()
    result = _prompt_to_dict(prompt)
    await db.commit()
    return result


@app.put("/api/v1/prompts/library/{prompt_id}")
async def update_prompt(prompt_id: str, body: PromptUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalars().first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if body.name is not None:
        prompt.name = body.name
    if body.promptText is not None:
        prompt.prompt_text = body.promptText
    if body.category is not None:
        prompt.category = body.category
    if body.tags is not None:
        prompt.tags = body.tags
    if body.isPublic is not None:
        prompt.is_public = body.isPublic

    prompt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prompt)
    return _prompt_to_dict(prompt)


@app.delete("/api/v1/prompts/library/{prompt_id}")
async def delete_prompt(prompt_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalars().first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    await db.delete(prompt)
    await db.commit()
    return {"message": "Prompt deleted"}


# --- Variations ---

@app.get("/api/v1/variations/history")
async def list_variations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Variation))
    variations = result.scalars().all()
    return {"data": [_variation_to_dict(v) for v in variations]}


@app.patch("/api/v1/variations/{variation_id}")
async def update_variation(variation_id: str, body: VariationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Variation).where(Variation.id == variation_id))
    variation = result.scalars().first()
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")

    if body.rating is not None:
        variation.rating = body.rating
    if body.notes is not None:
        variation.notes = body.notes

    await db.commit()
    await db.refresh(variation)
    return _variation_to_dict(variation)


@app.delete("/api/v1/variations/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Variation))
    variations = result.scalars().all()
    count = len(variations)
    for v in variations:
        await db.delete(v)
    await db.commit()
    return {"message": "History cleared", "deleted": count}


@app.delete("/api/v1/variations/{variation_id}")
async def delete_variation(variation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Variation).where(Variation.id == variation_id))
    variation = result.scalars().first()
    if not variation:
        raise HTTPException(status_code=404, detail="Variation not found")

    await db.delete(variation)
    await db.commit()
    return {"message": "Variation deleted"}


# --- Image Generation ---

async def generate_image(
    prompt: str,
    model: str,
    style: str = "coloring_book",
    seed: Optional[int] = None,
) -> dict:
    """Call external image generation API and return result.

    This function is the mockable seam for tests. In production it calls
    the configured provider (DALL-E 3, SDXL, Imagen).

    Returns:
        dict with keys: image_url, seed, model
    """
    actual_seed = seed if seed is not None else random.randint(0, 2**31)
    # Placeholder: in production, dispatch to real provider based on model
    # For now, return a generated URL pattern
    image_url = f"https://api.example.com/generated/{model}/{actual_seed}.png"
    return {"image_url": image_url, "seed": actual_seed, "model": model}


@app.post("/api/v1/generate", status_code=201)
async def generate(body: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a coloring book image using the specified model."""
    try:
        result = await generate_image(
            prompt=body.prompt,
            model=body.model.value,
            style=body.style,
            seed=body.seed,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Image generation timed out")
    except Exception as exc:
        logger.warning(f"Image generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}")

    variation = Variation(
        prompt=body.prompt,
        model=result["model"],
        image_url=result["image_url"],
        seed=result["seed"],
        parameters={"style": body.style},
    )
    db.add(variation)
    await db.flush()
    response = _variation_to_dict(variation)
    await db.commit()
    return response
