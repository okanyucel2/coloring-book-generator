"""Pydantic request/response schemas"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ModelName(str, Enum):
    dalle3 = "dalle3"
    sdxl = "sdxl"
    imagen = "imagen"


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    promptText: str = Field(..., alias="promptText", min_length=1, max_length=2000)
    category: str = ""
    tags: list[str] = []
    isPublic: bool = Field(False, alias="isPublic")

    model_config = {"populate_by_name": True}


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    promptText: Optional[str] = Field(None, alias="promptText", min_length=1, max_length=2000)
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    isPublic: Optional[bool] = Field(None, alias="isPublic")

    model_config = {"populate_by_name": True}


class VariationUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    model: ModelName
    style: str = "coloring_book"
    seed: Optional[int] = None
