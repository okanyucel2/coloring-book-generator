"""SQLAlchemy models for Coloring Book API"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Boolean, Integer, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./coloring_book_api.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)


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
    status = Column(String(20), default="draft")
    progress = Column(Float, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    etsy_listing_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
