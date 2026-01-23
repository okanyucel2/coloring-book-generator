"""Tests for MetadataGenerator class."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
import json
from datetime import datetime
from coloring_book.metadata import (
    PackageMetadata,
    AnimalMetadata,
    DifficultyLevel,
    AgeGroup,
    FileFormat,
)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    animals = [
        AnimalMetadata(
            name="Lion",
            species="Panthera leo",
            description="King of the jungle",
            difficulty=DifficultyLevel.MEDIUM,
            age_groups=[AgeGroup.ELEMENTARY, AgeGroup.PRETEEN],
            tags=["big_cat", "africa", "mane"],
            fun_fact="Lions are the only social cats",
            coloring_time_minutes=15,
        ),
        AnimalMetadata(
            name="Butterfly",
            species="Papilionoidea",
            description="Colorful winged insect",
            difficulty=DifficultyLevel.EASY,
            age_groups=[AgeGroup.PRESCHOOL, AgeGroup.EARLY_ELEMENTARY],
            tags=["insect", "wings", "colorful"],
            fun_fact="Butterflies taste with their feet",
            coloring_time_minutes=8,
        ),
    ]
    
    return PackageMetadata(
        title="Amazing Animals",
        description="A collection of animal drawings for kids",
        version="1.0.0",
        animals=animals,
        total_pages=10,
        difficulty_level=DifficultyLevel.MIXED,
        target_age_groups=[AgeGroup.ELEMENTARY, AgeGroup.PRETEEN],
        created_by="GENESIS",
        estimated_total_time_hours=2.5,
        keywords=["animals", "nature", "kids", "coloring"],
        category="Coloring Books",
        subcategory="Animals",
    )


@pytest.fixture
def generator(sample_metadata):
    """Create MetadataGenerator instance."""
    from coloring_book.metadata.generator import MetadataGenerator
    return MetadataGenerator(sample_metadata)


class TestMetadataGeneratorBasics:
    """Test basic MetadataGenerator functionality."""
    
    def test_generator_initialization(self, generator, sample_metadata):
        """Test generator initializes with metadata."""
        assert generator.metadata == sample_metadata
        assert generator.metadata.title == "Amazing Animals"
    
    def test_generator_has_metadata_property(self, generator):
        """Test generator exposes metadata property."""
        assert hasattr(generator, "metadata")
        assert isinstance(generator.metadata, PackageMetadata)


class TestJSONExport:
    """Test JSON export functionality."""
    
    def test_to_json_returns_valid_json(self, generator):
        """Test to_json() returns valid JSON string."""
        json_str = generator.to_json()
        assert isinstance(json_str, str)
        # Should be parseable as JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
    
    def test_json_contains_required_fields(self, generator):
        """Test JSON export contains all required fields."""
        json_str = generator.to_json()
        data = json.loads(json_str)
        
        required_fields = [
            "title",
            "description",
            "version",
            "total_pages",
            "difficulty_level",
            "target_age_groups",
            "animals",
            "keywords",
            "category",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_json_animals_include_metadata(self, generator):
        """Test JSON includes full animal metadata."""
        json_str = generator.to_json()
        data = json.loads(json_str)
        
        animals = data["animals"]
        assert len(animals) == 2
        assert animals[0]["name"] == "Lion"
        assert animals[0]["fun_fact"] == "Lions are the only social cats"
        assert animals[0]["coloring_time_minutes"] == 15
    
    def test_to_json_pretty_formatting(self, generator):
        """Test to_json() with pretty=True returns formatted JSON."""
        json_str = generator.to_json(pretty=True)
        assert "\n" in json_str  # Should have newlines for formatting
        assert "  " in json_str  # Should have indentation
    
    def test_json_datetimes_converted_to_iso(self, generator):
        """Test datetime objects are converted to ISO format."""
        json_str = generator.to_json()
        data = json.loads(json_str)
        
        # created_date should be ISO format string
        assert isinstance(data["created_date"], str)
        assert "T" in data["created_date"]  # ISO format has T separator


class TestTXTExport:
    """Test TXT export functionality."""
    
    def test_to_txt_returns_string(self, generator):
        """Test to_txt() returns string."""
        txt = generator.to_txt()
        assert isinstance(txt, str)
    
    def test_txt_contains_title(self, generator):
        """Test TXT export contains title."""
        txt = generator.to_txt()
        assert "Amazing Animals" in txt
    
    def test_txt_contains_all_animals(self, generator):
        """Test TXT includes all animal names."""
        txt = generator.to_txt()
        assert "LION" in txt
        assert "BUTTERFLY" in txt
    
    def test_txt_contains_animal_details(self, generator):
        """Test TXT includes detailed animal information."""
        txt = generator.to_txt()
        assert "King of the jungle" in txt
        assert "Lions are the only social cats" in txt
        assert "15 minutes" in txt  # Coloring time
    
    def test_txt_contains_publishing_info(self, generator):
        """Test TXT includes publishing section."""
        txt = generator.to_txt()
        assert "PUBLISHING INFO" in txt
        assert "Coloring Books" in txt
        assert "Animals" in txt
    
    def test_txt_contains_keywords(self, generator):
        """Test TXT includes keywords."""
        txt = generator.to_txt()
        assert "KEYWORDS" in txt
        assert "animals" in txt
        assert "nature" in txt
    
    def test_txt_human_readable_format(self, generator):
        """Test TXT is human-readable with sections."""
        txt = generator.to_txt()
        sections = [
            "CONTENT DETAILS",
            "ANIMALS",
            "PUBLISHING INFO",
            "RECOMMENDATIONS",
            "KEYWORDS",
            "METADATA",
        ]
        for section in sections:
            assert section in txt


class TestFileExport:
    """Test file export functionality."""
    
    def test_export_to_json_file(self, generator, tmp_path):
        """Test exporting metadata to JSON file."""
        output_file = tmp_path / "metadata.json"
        result = generator.export_json(str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify content
        with open(output_file) as f:
            data = json.load(f)
            assert data["title"] == "Amazing Animals"
            assert len(data["animals"]) == 2
    
    def test_export_to_txt_file(self, generator, tmp_path):
        """Test exporting metadata to TXT file."""
        output_file = tmp_path / "metadata.txt"
        result = generator.export_txt(str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify content
        with open(output_file) as f:
            content = f.read()
            assert "Amazing Animals" in content
            assert "LION" in content
    
    def test_export_both_formats(self, generator, tmp_path):
        """Test exporting to both JSON and TXT."""
        json_file = tmp_path / "metadata.json"
        txt_file = tmp_path / "metadata.txt"
        
        generator.export_json(str(json_file))
        generator.export_txt(str(txt_file))
        
        assert json_file.exists()
        assert txt_file.exists()


class TestMetadataGeneration:
    """Test metadata generation from packages."""
    
    def test_generate_metadata_dict(self, generator):
        """Test metadata can be represented as dictionary."""
        metadata_dict = generator.to_dict()
        assert isinstance(metadata_dict, dict)
        assert metadata_dict["title"] == "Amazing Animals"
    
    def test_get_summary_statistics(self, generator):
        """Test generator can provide summary stats."""
        stats = generator.get_stats()
        
        assert stats["total_animals"] == 2
        assert stats["total_pages"] == 10
        assert stats["estimated_hours"] == 2.5
        assert "animals_by_difficulty" in stats
        assert "animals_by_age_group" in stats
    
    def test_stats_count_animals_by_difficulty(self, generator):
        """Test stats correctly count animals by difficulty."""
        stats = generator.get_stats()
        difficulty_stats = stats["animals_by_difficulty"]
        
        assert difficulty_stats[DifficultyLevel.EASY.value] == 1
        assert difficulty_stats[DifficultyLevel.MEDIUM.value] == 1
    
    def test_stats_count_animals_by_age_group(self, generator):
        """Test stats correctly count animals by age group."""
        stats = generator.get_stats()
        age_stats = stats["animals_by_age_group"]
        
        # Lion: ELEMENTARY, PRETEEN
        # Butterfly: PRESCHOOL, EARLY_ELEMENTARY
        assert age_stats[AgeGroup.PRETEEN.value] == 1  # Only lion
        assert age_stats[AgeGroup.PRESCHOOL.value] == 1  # Only butterfly
        assert age_stats[AgeGroup.EARLY_ELEMENTARY.value] == 1  # Only butterfly


class TestMetadataValidation:
    """Test metadata validation."""
    
    def test_validate_required_fields(self, generator):
        """Test validation checks required fields."""
        is_valid = generator.validate()
        assert is_valid is True
    
    def test_validation_report(self, generator):
        """Test validation returns detailed report."""
        is_valid, report = generator.validate_detailed()
        assert is_valid is True
        assert isinstance(report, dict)
        assert "errors" in report
        assert "warnings" in report
        assert len(report["errors"]) == 0
    
    def test_validation_fails_missing_title(self):
        """Test validation fails with missing title."""
        bad_metadata = PackageMetadata(
            title="",  # Empty title
            description="Test",
            animals=[],
        )
        from coloring_book.metadata.generator import MetadataGenerator
        generator = MetadataGenerator(bad_metadata)
        is_valid, report = generator.validate_detailed()
        
        assert is_valid is False
        assert len(report["errors"]) > 0
    
    def test_validation_warns_empty_animals(self):
        """Test validation warns about empty animals list."""
        bad_metadata = PackageMetadata(
            title="Test",
            description="Test",
            animals=[],  # Empty animals
        )
        from coloring_book.metadata.generator import MetadataGenerator
        generator = MetadataGenerator(bad_metadata)
        is_valid, report = generator.validate_detailed()
        
        # Should still be valid but with warning
        assert len(report["warnings"]) > 0


class TestMetadataUpdate:
    """Test metadata update functionality."""
    
    def test_update_title(self, generator):
        """Test updating metadata title."""
        generator.update_title("New Title")
        assert generator.metadata.title == "New Title"
    
    def test_update_description(self, generator):
        """Test updating metadata description."""
        generator.update_description("New description")
        assert generator.metadata.description == "New description"
    
    def test_add_keyword(self, generator):
        """Test adding keywords."""
        initial_count = len(generator.metadata.keywords)
        generator.add_keyword("fun")
        assert len(generator.metadata.keywords) == initial_count + 1
        assert "fun" in generator.metadata.keywords
    
    def test_update_timestamps(self, generator):
        """Test timestamp updates when modifying."""
        old_updated = generator.metadata.updated_date
        generator.update_description("Changed")
        new_updated = generator.metadata.updated_date
        
        # Should be updated (at minimum equal, likely newer)
        assert new_updated >= old_updated
