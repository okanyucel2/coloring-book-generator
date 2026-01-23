"""Metadata module for coloring book packages."""

from .schema import (
    DifficultyLevel,
    AgeGroup,
    FileFormat,
    AnimalMetadata,
    PackageMetadata,
)
from .generator import MetadataGenerator

__all__ = [
    "DifficultyLevel",
    "AgeGroup",
    "FileFormat",
    "AnimalMetadata",
    "PackageMetadata",
    "MetadataGenerator",
]
