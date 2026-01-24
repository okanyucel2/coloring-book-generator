"""
RED PHASE: Tests for variation generation API endpoint.
Tests written FIRST - implementation comes next (TDD).
"""

import pytest
import json
from typing import Dict, List
from src.components.prompt_template_service import (
    PromptVariationService, PromptTemplate, VariationConfig
)


class TestVariationGenerationService:
    """Tests for backend variation generation service."""
    
    @pytest.fixture
    def service(self):
        """Create service without presets for clean test isolation."""
        return PromptVariationService(load_presets=False)
    
    @pytest.fixture
    def sample_template(self):
        """Create a sample template with variables."""
        return PromptTemplate(
            name="Test Template",
            template_text="Draw a {{animal}} in {{style}} style"
        )
    
    def test_generate_variations_with_seed_deterministic(self, service, sample_template):
        """Test that same seed produces same variations."""
        # Add template
        template_id = service.add_template(sample_template)
        
        # Generate variations with seed 42
        config1 = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": ["cat", "dog", "bird"],
                "style": ["watercolor", "oil painting", "sketch"]
            },
            seed=42
        )
        result1 = service.generate_variations(config1)
        
        # Generate again with same seed
        config2 = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": ["cat", "dog", "bird"],
                "style": ["watercolor", "oil painting", "sketch"]
            },
            seed=42
        )
        result2 = service.generate_variations(config2)
        
        # Results must be identical
        assert result1 == result2, "Same seed should produce identical variations"
        assert len(result1) == 5
    
    def test_generate_variations_different_seeds_differ(self, service, sample_template):
        """Test that different seeds produce different variations."""
        template_id = service.add_template(sample_template)
        
        config1 = VariationConfig(
            template_id=template_id,
            variations=10,
            variables={
                "animal": ["cat", "dog", "bird"],
                "style": ["watercolor", "oil painting", "sketch"]
            },
            seed=42
        )
        result1 = service.generate_variations(config1)
        
        config2 = VariationConfig(
            template_id=template_id,
            variations=10,
            variables={
                "animal": ["cat", "dog", "bird"],
                "style": ["watercolor", "oil painting", "sketch"]
            },
            seed=99
        )
        result2 = service.generate_variations(config2)
        
        # Results should be different (statistically impossible to be same)
        assert result1 != result2, "Different seeds should produce different variations"
    
    def test_generate_variations_without_seed_random(self, service, sample_template):
        """Test that without seed, variations are random."""
        template_id = service.add_template(sample_template)
        
        results = []
        for _ in range(3):
            config = VariationConfig(
                template_id=template_id,
                variations=5,
                variables={
                    "animal": ["cat", "dog", "bird"],
                    "style": ["watercolor", "oil painting", "sketch"]
                },
                seed=None  # No seed = random
            )
            results.append(service.generate_variations(config))
        
        # At least one should differ (statistically almost certain)
        assert results[0] != results[1] or results[1] != results[2], "Without seed should be random"
    
    def test_generate_variations_batch_size(self, service, sample_template):
        """Test generating different batch sizes."""
        template_id = service.add_template(sample_template)
        
        for num_variations in [1, 5, 10, 20]:
            config = VariationConfig(
                template_id=template_id,
                variations=num_variations,
                variables={
                    "animal": ["cat", "dog"],
                    "style": ["watercolor", "oil"]
                },
                seed=42
            )
            result = service.generate_variations(config)
            assert len(result) == num_variations, f"Should generate {num_variations} variations"
    
    def test_generate_variations_substitutes_all_variables(self, service, sample_template):
        """Test that all variables in template are substituted."""
        template_id = service.add_template(sample_template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": ["cat"],
                "style": ["watercolor"]
            },
            seed=42
        )
        result = service.generate_variations(config)
        
        # All results should contain the substituted values, not {{variable}}
        for variation in result:
            assert "{{animal}}" not in variation, "Should not contain unreplaced {{animal}}"
            assert "{{style}}" not in variation, "Should not contain unreplaced {{style}}"
            assert "cat" in variation, "Should contain substituted animal"
            assert "watercolor" in variation, "Should contain substituted style"
    
    def test_generate_variations_invalid_template(self, service):
        """Test error handling for invalid template ID."""
        config = VariationConfig(
            template_id="nonexistent_id",
            variations=5,
            variables={"animal": ["cat"]},
            seed=42
        )
        
        with pytest.raises(ValueError, match="Template not found"):
            service.generate_variations(config)
    
    def test_generate_variations_empty_options(self, service, sample_template):
        """Test error handling for empty variable options."""
        template_id = service.add_template(sample_template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": [],  # Empty options
                "style": ["watercolor"]
            },
            seed=42
        )
        
        with pytest.raises(ValueError, match="has no options"):
            service.generate_variations(config)
    
    def test_generate_variations_missing_variables_get_default(self, service, sample_template):
        """Test that missing variables get 'default' value."""
        template_id = service.add_template(sample_template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": ["cat"]
                # Note: "style" is missing
            },
            seed=42
        )
        result = service.generate_variations(config)
        
        # All should contain "cat" and "default" for missing style
        for variation in result:
            assert "cat" in variation, "Should contain animal"
            assert "default" in variation, "Missing variable should be replaced with 'default'"
    
    def test_generate_variations_single_option(self, service, sample_template):
        """Test with single option per variable (deterministic output)."""
        template_id = service.add_template(sample_template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={
                "animal": ["cat"],
                "style": ["watercolor"]
            },
            seed=42
        )
        result = service.generate_variations(config)
        
        # All variations should be identical since only one option per variable
        expected = "Draw a cat in watercolor style"
        for variation in result:
            assert variation == expected, f"Expected '{expected}', got '{variation}'"
    
    def test_generate_variations_multiple_variables(self, service):
        """Test template with 4+ variables."""
        template = PromptTemplate(
            name="Complex Template",
            template_text="A {{emotion}} {{animal}} {{action}} in {{location}}"
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            variables={
                "emotion": ["happy", "sad"],
                "animal": ["cat", "dog"],
                "action": ["running", "sleeping"],
                "location": ["park", "home", "forest"]
            },
            seed=42
        )
        result = service.generate_variations(config)
        
        assert len(result) == 3
        for variation in result:
            assert "{{" not in variation, "All variables should be replaced"
            assert any(e in variation for e in ["happy", "sad"])
            assert any(a in variation for a in ["cat", "dog"])


class TestVariationGenerationAPI:
    """Tests for REST API endpoint handling."""
    
    def test_api_endpoint_exists(self):
        """Test that API endpoint is registered."""
        # This will be implemented when endpoint is created
        pass
    
    def test_api_generate_variations_request(self):
        """Test API request with valid payload."""
        # Payload structure:
        payload = {
            "template_id": "template_123",
            "num_variations": 5,
            "variables": {
                "animal": ["cat", "dog"],
                "style": ["watercolor"]
            },
            "seed": 42
        }
        # Should return 200 with generated variations
        pass
    
    def test_api_missing_template_id(self):
        """Test API with missing template_id."""
        # Should return 400 Bad Request
        pass
    
    def test_api_invalid_num_variations(self):
        """Test API with invalid num_variations."""
        # Should return 400 Bad Request
        pass
    
    def test_api_response_format(self):
        """Test API response contains expected fields."""
        # Response should have: variations[], seed, template_id, generated_at
        pass


class TestVariationGenerationEdgeCases:
    """Edge case tests for variation generation."""
    
    @pytest.fixture
    def service(self):
        return PromptVariationService(load_presets=False)
    
    def test_generate_variations_with_special_characters(self, service):
        """Test template with special characters in variables."""
        template = PromptTemplate(
            name="Special Char Template",
            template_text="Draw {{item}} with {{style}}"
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            variables={
                "item": ["cat & dog", "bird (flying)", "fish/shark"],
                "style": ["oil & watercolor", "pencil (sketch)"]
            },
            seed=42
        )
        result = service.generate_variations(config)
        
        # Should handle special characters
        assert len(result) == 3
        assert all("&" in var or "(" in var or "/" in var for var in result)
    
    def test_generate_variations_large_batch(self, service):
        """Test generating large batch (100+ variations)."""
        template = PromptTemplate(
            name="Template",
            template_text="Draw {{animal}}"
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=100,
            variables={"animal": ["cat", "dog", "bird"]},
            seed=42
        )
        result = service.generate_variations(config)
        
        assert len(result) == 100
        assert all(isinstance(v, str) for v in result)
    
    def test_generate_variations_seed_zero(self, service):
        """Test with seed value 0 (falsy but valid)."""
        template = PromptTemplate(
            name="Template",
            template_text="Draw {{animal}}"
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={"animal": ["cat", "dog"]},
            seed=0  # Falsy value but valid seed
        )
        result = service.generate_variations(config)
        
        assert len(result) == 5
    
    def test_generate_variations_negative_seed(self, service):
        """Test with negative seed (valid in Python random)."""
        template = PromptTemplate(
            name="Template",
            template_text="Draw {{animal}}"
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={"animal": ["cat"]},
            seed=-42  # Negative seed
        )
        result = service.generate_variations(config)
        
        assert len(result) == 5
    
    def test_generate_variations_very_long_template(self, service):
        """Test with very long template text."""
        long_text = "Draw " + "a beautiful " * 100 + "{{animal}}"
        template = PromptTemplate(
            name="Long Template",
            template_text=long_text
        )
        template_id = service.add_template(template)
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            variables={"animal": ["cat"]},
            seed=42
        )
        result = service.generate_variations(config)
        
        assert len(result) == 3
        assert all(len(v) > 500 for v in result)
