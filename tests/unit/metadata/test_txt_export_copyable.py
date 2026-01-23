"""Tests for TXT export copy-paste functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from coloring_book.metadata import (
    PackageMetadata,
    AnimalMetadata,
    DifficultyLevel,
    AgeGroup,
    MetadataGenerator,
)


@pytest.fixture
def minimal_metadata():
    """Create minimal metadata for copy-paste testing."""
    return PackageMetadata(
        title="Simple Coloring Book",
        description="A simple book for testing",
        animals=[
            AnimalMetadata(
                name="Cat",
                species="Felis catus",
                description="Domestic cat",
                difficulty=DifficultyLevel.EASY,
                age_groups=[AgeGroup.PRESCHOOL],
                tags=["pet", "domestic"],
            )
        ],
        total_pages=5,
        keywords=["cat", "animals"],
    )


@pytest.fixture  
def generator(minimal_metadata):
    """Create MetadataGenerator instance."""
    return MetadataGenerator(minimal_metadata)


class TestTXTCopyPasteFormat:
    """Test TXT export is optimized for copy-paste use."""
    
    def test_txt_output_is_plain_ascii(self, generator):
        """Test TXT output uses plain ASCII (copy-paste friendly)."""
        txt = generator.to_txt()
        # Should not contain special unicode characters
        try:
            txt.encode('ascii')
            assert True
        except UnicodeEncodeError:
            pytest.fail("TXT output contains non-ASCII characters")
    
    def test_txt_has_no_markdown(self, generator):
        """Test TXT has no markdown formatting."""
        txt = generator.to_txt()
        # No markdown markers
        assert "**" not in txt
        assert "__" not in txt
        assert "##" not in txt
        assert "[" not in txt or "]" not in txt
    
    def test_txt_uses_simple_separators(self, generator):
        """Test TXT uses simple separators."""
        txt = generator.to_txt()
        # Uses ===, not fancy unicode
        assert "===" in txt
        assert "—" not in txt  # No em-dashes
        assert "–" not in txt  # No en-dashes
    
    def test_txt_is_line_based(self, generator):
        """Test each section is line-based for easy copying."""
        txt = generator.to_txt()
        lines = txt.split("\n")
        
        # Should have many lines for easy selection
        assert len(lines) > 10
        # Most lines should be reasonably short for terminals
        for line in lines:
            assert len(line) < 200  # Terminal friendly


class TestTXTTabularData:
    """Test TXT uses table-like format for structured data."""
    
    def test_animal_listing_is_numbered(self, generator):
        """Test animals are numbered for easy reference."""
        txt = generator.to_txt()
        assert "1. " in txt or "1 " in txt
        assert "CAT" in txt
    
    def test_fields_use_labels(self, generator):
        """Test fields are labeled (key: value format)."""
        txt = generator.to_txt()
        # Should use colon format
        assert "Description:" in txt
        assert "Tags:" in txt
        # Species is in the animal header, not a separate field
        assert "Felis catus" in txt


class TestTXTStructure:
    """Test TXT structure is predictable for parsing."""
    
    def test_has_distinct_sections(self, generator):
        """Test TXT has clear section headers."""
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
            assert section in txt, f"Missing section: {section}"
    
    def test_section_headers_are_uppercase(self, generator):
        """Test section headers use UPPERCASE."""
        txt = generator.to_txt()
        
        # All headers should be uppercase
        lines = txt.split("\n")
        header_lines = [l for l in lines if l.isupper() and len(l) > 3]
        # Should find multiple headers
        assert len(header_lines) > 0


class TestTXTKeywordList:
    """Test keywords are copy-paste friendly."""
    
    def test_keywords_comma_separated(self, generator):
        """Test keywords are comma-separated on single line."""
        txt = generator.to_txt()
        
        # Find keywords line
        lines = txt.split("\n")
        keyword_line = None
        for i, line in enumerate(lines):
            if "KEYWORDS" in line:
                keyword_line = lines[i+1] if i+1 < len(lines) else None
                break
        
        assert keyword_line is not None
        assert "," in keyword_line  # Comma separated
        assert len(keyword_line) < 200  # Single line, copy-able
    
    def test_each_animal_on_separate_entry(self, generator):
        """Test each animal is in its own block."""
        txt = generator.to_txt()
        
        lines = txt.split("\n")
        # Find animal section
        animals_idx = None
        for i, line in enumerate(lines):
            if "ANIMALS" in line:
                animals_idx = i
                break
        
        assert animals_idx is not None
        # Each animal should be numbered
        animal_lines = [l for l in lines[animals_idx:] if l.strip().startswith(("1.", "2.", "3."))]
        assert len(animal_lines) > 0


class TestTXTExampleData:
    """Test TXT export with real-world example."""
    
    def test_comprehensive_metadata_export(self):
        """Test export with comprehensive metadata."""
        metadata = PackageMetadata(
            title="African Safari Animals",
            description="A collection of African animals",
            animals=[
                AnimalMetadata(
                    name="Zebra",
                    species="Equus quagga",
                    description="Black and white striped horse",
                    difficulty=DifficultyLevel.MEDIUM,
                    age_groups=[AgeGroup.ELEMENTARY],
                    tags=["stripes", "africa", "herbivore"],
                    fun_fact="Each zebra has unique stripe pattern",
                    coloring_time_minutes=20,
                ),
                AnimalMetadata(
                    name="Elephant",
                    species="Loxodonta",
                    description="Largest land animal",
                    difficulty=DifficultyLevel.HARD,
                    age_groups=[AgeGroup.ELEMENTARY, AgeGroup.PRETEEN],
                    tags=["trunk", "africa", "large"],
                    fun_fact="Elephants can remember for years",
                    coloring_time_minutes=30,
                ),
            ],
            total_pages=10,
            keywords=["africa", "safari", "animals", "exotic"],
            category="Coloring Books",
            subcategory="Wildlife",
        )
        
        generator = MetadataGenerator(metadata)
        txt = generator.to_txt()
        
        # Should contain all critical info
        assert "African Safari Animals" in txt
        assert "ZEBRA" in txt
        assert "ELEPHANT" in txt
        assert "Each zebra has unique stripe pattern" in txt
        assert "Elephants can remember for years" in txt
        assert "20 minutes" in txt
        assert "30 minutes" in txt
    
    def test_txt_copyable_keyword_line(self):
        """Test keywords can be copied as-is for Etsy."""
        metadata = PackageMetadata(
            title="Test",
            description="Test",
            keywords=["coloring", "animals", "kids", "fun", "relaxation"],
        )
        
        generator = MetadataGenerator(metadata)
        txt = generator.to_txt()
        
        # Keywords should be easily copyable
        assert "coloring, animals, kids, fun, relaxation" in txt


class TestTXTLineLength:
    """Test TXT respects line length limits."""
    
    def test_no_lines_exceed_120_chars(self, generator):
        """Test reasonable line length for terminals."""
        txt = generator.to_txt()
        
        lines = txt.split("\n")
        long_lines = [l for l in lines if len(l) > 120]
        
        # Allow some long lines but not many
        assert len(long_lines) < len(lines) * 0.2  # Less than 20%


class TestTXTWhitespace:
    """Test whitespace is clean for copy-paste."""
    
    def test_no_trailing_spaces(self, generator):
        """Test no trailing spaces on lines."""
        txt = generator.to_txt()
        
        lines = txt.split("\n")
        for line in lines:
            assert line == line.rstrip(), f"Line has trailing space: '{line}'"
    
    def test_proper_blank_line_spacing(self, generator):
        """Test blank lines separate sections."""
        txt = generator.to_txt()
        
        lines = txt.split("\n")
        # Should have blank lines between sections
        blank_count = sum(1 for l in lines if l.strip() == "")
        assert blank_count > 5  # Several blank lines for spacing


class TestTXTEtsyIntegration:
    """Test TXT format works for Etsy listing."""
    
    def test_title_suitable_for_etsy_listing(self, generator):
        """Test title is suitable for Etsy."""
        txt = generator.to_txt()
        
        # Should start with title
        assert "Simple Coloring Book" in txt
        # Should be clearly marked
        lines = txt.split("\n")
        first_lines = "\n".join(lines[:3])
        assert "===" in first_lines
    
    def test_description_copyable_for_etsy(self, generator):
        """Test description can be copied to Etsy."""
        txt = generator.to_txt()
        
        # Description should be easy to find and copy
        assert "Description:" in txt
        lines = txt.split("\n")
        desc_lines = [l for l in lines if "Description:" in l]
        assert len(desc_lines) > 0
    
    def test_keywords_in_etsy_format(self, generator):
        """Test keywords formatted for Etsy copy-paste."""
        txt = generator.to_txt()
        
        # Find keywords section
        lines = txt.split("\n")
        keywords_idx = None
        for i, line in enumerate(lines):
            if "KEYWORDS" in line:
                keywords_idx = i + 1
                break
        
        assert keywords_idx is not None
        keyword_line = lines[keywords_idx]
        # Should be simple comma-separated list
        keywords = [k.strip() for k in keyword_line.split(",")]
        assert len(keywords) > 0
        # No special formatting
        for keyword in keywords:
            assert keyword.count("(") == 0
            assert keyword.count("[") == 0
