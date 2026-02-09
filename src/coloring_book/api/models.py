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
