"""SQLAlchemy models for Coloring Book API"""
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, LargeBinary, ForeignKey, UniqueConstraint, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Async engine (primary — used by all FastAPI route handlers)
# Use project-specific env var; falls back to generic DATABASE_URL only if it's SQLite-compatible
_default_url = "sqlite+aiosqlite:///./coloring_book_api.db"
DATABASE_URL = os.environ.get("COLORING_BOOK_DATABASE_URL", _default_url)
engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine (used only by _generate_pdf background task)
SYNC_DATABASE_URL = DATABASE_URL.replace("+aiosqlite", "")
sync_engine = create_engine(SYNC_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()


async def get_db():
    async with async_session() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    prompt_text = Column(Text, nullable=False)
    category = Column(String(50), default="")
    tags = Column(JSON, default=list)
    is_public = Column(Boolean, default=False)
    rating = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Variation(Base):
    __tablename__ = "variations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    image_url = Column(String(500), default="")
    rating = Column(Integer, default=0)
    seed = Column(Integer, default=0)
    notes = Column(Text, default="")
    parameters = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WorkbookModel(Base):
    __tablename__ = "workbooks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    theme = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200), nullable=True)
    age_min = Column(Integer, default=3)
    age_max = Column(Integer, default=5)
    page_count = Column(Integer, default=30)
    items_json = Column(JSON, default=list)
    activity_mix_json = Column(JSON, default=dict)
    page_size = Column(String(10), default="letter")
    image_source = Column(String(20), default="auto")
    variation_image_map_json = Column(JSON, nullable=True)
    status = Column(String(20), default="draft")
    progress = Column(Float, nullable=True)
    generation_stage = Column(String(50), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    generation_cost_usd = Column(Float, default=0.0)
    etsy_listing_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    avatar_url = Column(String(500), nullable=True)
    provider = Column(String(20), default="google")
    provider_id = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)


class ProviderToken(Base):
    __tablename__ = "provider_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    encrypted_access_token = Column(LargeBinary, nullable=False)
    encrypted_refresh_token = Column(LargeBinary, nullable=True)
    scopes = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    provider_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))
