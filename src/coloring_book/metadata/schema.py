"""Metadata schema definitions for coloring book packages."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    """Difficulty levels for coloring books."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class AgeGroup(str, Enum):
    """Target age groups."""
    TODDLER = "toddler"  # 2-4
    PRESCHOOL = "preschool"  # 4-6
    EARLY_ELEMENTARY = "early_elementary"  # 6-8
    ELEMENTARY = "elementary"  # 8-10
    PRETEEN = "preteen"  # 10-12
    TEEN = "teen"  # 12+
    ADULT = "adult"


class FileFormat(str, Enum):
    """Output file formats."""
    PDF = "pdf"
    PNG = "png"
    SVG = "svg"
    ZIP = "zip"


@dataclass
class AnimalMetadata:
    """Metadata for individual animals."""
    name: str
    species: str
    description: str
    difficulty: DifficultyLevel
    age_groups: List[AgeGroup]
    tags: List[str] = field(default_factory=list)
    fun_fact: Optional[str] = None
    coloring_time_minutes: Optional[int] = None


@dataclass
class PackageMetadata:
    """Complete metadata for a coloring book package."""
    # Basic info
    title: str
    description: str
    version: str = "1.0.0"
    
    # Content details
    animals: List[AnimalMetadata] = field(default_factory=list)
    total_pages: int = 0
    difficulty_level: DifficultyLevel = DifficultyLevel.MIXED
    target_age_groups: List[AgeGroup] = field(default_factory=list)
    
    # Creator/Source
    created_by: str = "GENESIS"
    created_date: datetime = field(default_factory=datetime.now)
    updated_date: datetime = field(default_factory=datetime.now)
    
    # Publishing
    publisher: str = "Etsy"
    sku: Optional[str] = None
    isbn: Optional[str] = None
    
    # Coloring details
    estimated_total_time_hours: float = 0.0
    paper_type_recommended: str = "White matte 80gsm"
    color_medium_recommended: str = "Colored pencils or markers"
    
    # SEO/Keywords
    keywords: List[str] = field(default_factory=list)
    category: str = "Coloring Books"
    subcategory: str = "Animals"
    
    # Files
    files: Dict[FileFormat, str] = field(default_factory=dict)  # Format -> filepath
    
    # Additional metadata
    language: str = "English"
    license: str = "Personal Use Only"
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "animals": [
                {
                    "name": animal.name,
                    "species": animal.species,
                    "description": animal.description,
                    "difficulty": animal.difficulty.value,
                    "age_groups": [ag.value for ag in animal.age_groups],
                    "tags": animal.tags,
                    "fun_fact": animal.fun_fact,
                    "coloring_time_minutes": animal.coloring_time_minutes,
                }
                for animal in self.animals
            ],
            "total_pages": self.total_pages,
            "difficulty_level": self.difficulty_level.value,
            "target_age_groups": [ag.value for ag in self.target_age_groups],
            "created_by": self.created_by,
            "created_date": self.created_date.isoformat(),
            "updated_date": self.updated_date.isoformat(),
            "publisher": self.publisher,
            "sku": self.sku,
            "isbn": self.isbn,
            "estimated_total_time_hours": self.estimated_total_time_hours,
            "paper_type_recommended": self.paper_type_recommended,
            "color_medium_recommended": self.color_medium_recommended,
            "keywords": self.keywords,
            "category": self.category,
            "subcategory": self.subcategory,
            "files": self.files,
            "language": self.language,
            "license": self.license,
            "custom_fields": self.custom_fields,
        }
    
    def to_txt(self) -> str:
        """Convert to human-readable TXT format."""
        age_groups_str = ", ".join(ag.value for ag in self.target_age_groups) if self.target_age_groups else "(none specified)"
        
        lines = [
            f"=== {self.title} ===",
            "",
            f"Description: {self.description}",
            f"Version: {self.version}",
            "",
            "CONTENT DETAILS",
            f"Total Pages: {self.total_pages}",
            f"Difficulty: {self.difficulty_level.value.upper()}",
            f"Target Age Groups: {age_groups_str}",
            f"Estimated Total Time: {self.estimated_total_time_hours} hours",
            "",
            "ANIMALS",
        ]
        
        for i, animal in enumerate(self.animals, 1):
            lines.extend([
                f"{i}. {animal.name.upper()} ({animal.species})",
                f"   Description: {animal.description}",
                f"   Difficulty: {animal.difficulty.value}",
                f"   Age Groups: {', '.join(ag.value for ag in animal.age_groups)}",
                f"   Tags: {', '.join(animal.tags) if animal.tags else '(none)'}",
            ])
            if animal.fun_fact:
                lines.append(f"   Fun Fact: {animal.fun_fact}")
            if animal.coloring_time_minutes:
                lines.append(f"   Coloring Time: ~{animal.coloring_time_minutes} minutes")
            lines.append("")
        
        lines.extend([
            "PUBLISHING INFO",
            f"Publisher: {self.publisher}",
            f"Category: {self.category} > {self.subcategory}",
            f"SKU: {self.sku or 'N/A'}",
            f"ISBN: {self.isbn or 'N/A'}",
            "",
            "RECOMMENDATIONS",
            f"Paper Type: {self.paper_type_recommended}",
            f"Color Medium: {self.color_medium_recommended}",
            "",
            "KEYWORDS",
            ", ".join(self.keywords) if self.keywords else "(none)",
            "",
            "METADATA",
            f"Created: {self.created_date.isoformat()}",
            f"Last Updated: {self.updated_date.isoformat()}",
            f"Language: {self.language}",
            f"License: {self.license}",
        ])
        
        if self.custom_fields:
            lines.extend(["", "CUSTOM FIELDS"])
            for key, value in self.custom_fields.items():
                lines.append(f"{key}: {value}")
        
        # Strip trailing spaces from all lines
        cleaned_lines = [line.rstrip() for line in lines]
        return "\n".join(cleaned_lines)
