"""MetadataGenerator class for managing coloring book metadata."""

import json
from typing import Dict, Any, Tuple, List
from datetime import datetime
from pathlib import Path

from .schema import (
    PackageMetadata,
    DifficultyLevel,
    AgeGroup,
    AnimalMetadata,
)


class MetadataGenerator:
    """Generate and manage metadata for coloring book packages."""
    
    def __init__(self, metadata: PackageMetadata):
        """Initialize generator with metadata."""
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return self.metadata.to_dict()
    
    def to_json(self, pretty: bool = False) -> str:
        """Convert metadata to JSON string.
        
        Args:
            pretty: If True, format with indentation
            
        Returns:
            JSON string representation of metadata
        """
        data = self.to_dict()
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)
    
    def to_txt(self) -> str:
        """Convert metadata to human-readable text format.
        
        Returns:
            Text string representation of metadata
        """
        return self.metadata.to_txt()
    
    def export_json(self, filepath: str) -> bool:
        """Export metadata to JSON file.
        
        Args:
            filepath: Path to write JSON file
            
        Returns:
            True if successful
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(self.to_json(pretty=True))
            return True
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
    
    def export_txt(self, filepath: str) -> bool:
        """Export metadata to TXT file.
        
        Args:
            filepath: Path to write TXT file
            
        Returns:
            True if successful
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(self.to_txt())
            return True
        except Exception as e:
            print(f"Error exporting TXT: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get metadata statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_animals": len(self.metadata.animals),
            "total_pages": self.metadata.total_pages,
            "estimated_hours": self.metadata.estimated_total_time_hours,
            "animals_by_difficulty": {},
            "animals_by_age_group": {},
        }
        
        # Count by difficulty
        for difficulty in DifficultyLevel:
            count = sum(
                1 for animal in self.metadata.animals
                if animal.difficulty == difficulty
            )
            if count > 0:
                stats["animals_by_difficulty"][difficulty.value] = count
        
        # Count by age group
        for age_group in AgeGroup:
            count = sum(
                1 for animal in self.metadata.animals
                if age_group in animal.age_groups
            )
            if count > 0:
                stats["animals_by_age_group"][age_group.value] = count
        
        return stats
    
    def validate(self) -> bool:
        """Validate metadata.
        
        Returns:
            True if metadata is valid
        """
        is_valid, _ = self.validate_detailed()
        return is_valid
    
    def validate_detailed(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate metadata with detailed report.
        
        Returns:
            Tuple of (is_valid, report_dict)
        """
        report = {
            "errors": [],
            "warnings": [],
        }
        
        # Required fields check
        if not self.metadata.title or self.metadata.title.strip() == "":
            report["errors"].append("Title is required and cannot be empty")
        
        if not self.metadata.description or self.metadata.description.strip() == "":
            report["errors"].append("Description is required and cannot be empty")
        
        # Warnings
        if len(self.metadata.animals) == 0:
            report["warnings"].append("No animals in package")
        
        if len(self.metadata.keywords) == 0:
            report["warnings"].append("No keywords defined")
        
        if not self.metadata.target_age_groups:
            report["warnings"].append("No target age groups specified")
        
        is_valid = len(report["errors"]) == 0
        return is_valid, report
    
    def update_title(self, new_title: str) -> None:
        """Update package title."""
        self.metadata.title = new_title
        self.metadata.updated_date = datetime.now()
    
    def update_description(self, new_description: str) -> None:
        """Update package description."""
        self.metadata.description = new_description
        self.metadata.updated_date = datetime.now()
    
    def add_keyword(self, keyword: str) -> None:
        """Add a keyword."""
        if keyword not in self.metadata.keywords:
            self.metadata.keywords.append(keyword)
        self.metadata.updated_date = datetime.now()
    
    def remove_keyword(self, keyword: str) -> None:
        """Remove a keyword."""
        if keyword in self.metadata.keywords:
            self.metadata.keywords.remove(keyword)
        self.metadata.updated_date = datetime.now()
    
    def add_animal(self, animal: AnimalMetadata) -> None:
        """Add an animal to the package."""
        self.metadata.animals.append(animal)
        self.metadata.updated_date = datetime.now()
    
    def remove_animal(self, animal_name: str) -> None:
        """Remove an animal by name."""
        self.metadata.animals = [
            a for a in self.metadata.animals 
            if a.name != animal_name
        ]
        self.metadata.updated_date = datetime.now()
    
    def get_animal_by_name(self, name: str) -> AnimalMetadata | None:
        """Get animal by name."""
        for animal in self.metadata.animals:
            if animal.name == name:
                return animal
        return None
    
    def update_total_time(self) -> None:
        """Calculate and update total coloring time based on animals."""
        total_minutes = sum(
            animal.coloring_time_minutes or 0
            for animal in self.metadata.animals
        )
        self.metadata.estimated_total_time_hours = total_minutes / 60
        self.metadata.updated_date = datetime.now()
    
    def update_page_count(self, count: int) -> None:
        """Update total page count."""
        self.metadata.total_pages = count
        self.metadata.updated_date = datetime.now()
    
    def export_all(self, directory: str) -> bool:
        """Export metadata in all formats to directory.
        
        Args:
            directory: Directory to export to
            
        Returns:
            True if all exports successful
        """
        try:
            base_path = Path(directory)
            base_path.mkdir(parents=True, exist_ok=True)
            
            success = True
            success &= self.export_json(str(base_path / "metadata.json"))
            success &= self.export_txt(str(base_path / "metadata.txt"))
            
            return success
        except Exception as e:
            print(f"Error exporting all: {e}")
            return False
