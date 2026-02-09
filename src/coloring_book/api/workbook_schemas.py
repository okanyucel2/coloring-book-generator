"""Pydantic schemas for workbook API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkbookCreate(BaseModel):
    """Request body for creating a new workbook."""

    theme: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    age_min: int = Field(3, ge=0, le=18)
    age_max: int = Field(5, ge=0, le=18)
    page_count: int = Field(30, ge=5, le=100)
    items: Optional[list[str]] = None  # None = auto-select from theme
    activity_mix: Optional[dict[str, int]] = None  # None = default distribution
    page_size: str = Field("letter", pattern="^(letter|a4)$")

    model_config = {"populate_by_name": True}


class WorkbookUpdate(BaseModel):
    """Request body for updating a workbook config."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    age_min: Optional[int] = Field(None, ge=0, le=18)
    age_max: Optional[int] = Field(None, ge=0, le=18)
    page_count: Optional[int] = Field(None, ge=5, le=100)
    items: Optional[list[str]] = None
    activity_mix: Optional[dict[str, int]] = None
    page_size: Optional[str] = Field(None, pattern="^(letter|a4)$")


class WorkbookResponse(BaseModel):
    """Response body for workbook details."""

    id: str
    theme: str
    title: str
    subtitle: Optional[str] = None
    age_min: int
    age_max: int
    page_count: int
    items: list[str]
    activity_mix: dict[str, int]
    page_size: str
    status: str  # "draft", "generating", "ready", "failed"
    progress: Optional[float] = None
    pdf_url: Optional[str] = None
    etsy_listing_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkbookStatusResponse(BaseModel):
    """Response body for generation status."""

    id: str
    status: str
    progress: Optional[float] = None
    error: Optional[str] = None


class ThemeResponse(BaseModel):
    """Response body for theme details."""

    slug: str
    display_name: str
    category: str
    items: list[str]
    item_count: int
    age_groups: list[str]
    etsy_tags: list[str]


class ThemeListResponse(BaseModel):
    """Response body for theme listing."""

    data: list[ThemeResponse]
