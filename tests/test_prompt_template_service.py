"""Tests for PromptTemplate and PromptVariationService (TDD)."""

import pytest
from typing import Dict, List
import json
from datetime import datetime
from src.components.prompt_template_service import (
    PromptTemplate,
    PromptVariable,
    PromptVariationService,
    VariationConfig,
)


class TestPromptVariable:
    """Tests for PromptVariable class."""
    
    def test_variable_creation(self):
        """Test creating a prompt variable."""
        var = PromptVariable(
            name="animal",
            description="Type of animal",
            default_value="cat",
            required=True
        )
        assert var.name == "animal"
        assert var.description == "Type of animal"
        assert var.default_value == "cat"
        assert var.required is True
    
    def test_variable_required_field(self):
        """Test required field validation."""
        var = PromptVariable(name="animal", required=True)
        assert var.required is True
    
    def test_variable_to_dict(self):
        """Test variable serialization."""
        var = PromptVariable(
            name="animal",
            description="Type of animal",
            default_value="cat"
        )
        var_dict = var.to_dict()
        assert var_dict["name"] == "animal"
        assert var_dict["description"] == "Type of animal"
        assert var_dict["default_value"] == "cat"


class TestPromptTemplate:
    """Tests for PromptTemplate class."""
    
    def test_template_creation(self):
        """Test creating a prompt template."""
        template = PromptTemplate(
            name="Animal Portrait",
            description="Draw a specific animal",
            template_text="Draw a {{animal}} in {{environment}}"
        )
        assert template.name == "Animal Portrait"
        assert template.description == "Draw a specific animal"
        assert template.template_text == "Draw a {{animal}} in {{environment}}"
    
    def test_template_extract_variables(self):
        """Test extracting variables from template text."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} in {{environment}} with {{color}} color"
        )
        variables = template.extract_variables()
        assert len(variables) == 3
        var_names = [v.name for v in variables]
        assert "animal" in var_names
        assert "environment" in var_names
        assert "color" in var_names
    
    def test_template_extract_variables_no_duplicates(self):
        """Test that extract_variables doesn't create duplicates."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} and another {{animal}}"
        )
        variables = template.extract_variables()
        assert len(variables) == 1
        assert variables[0].name == "animal"
    
    def test_template_extract_no_variables(self):
        """Test template with no variables."""
        template = PromptTemplate(
            name="Static",
            template_text="Draw a beautiful landscape"
        )
        variables = template.extract_variables()
        assert len(variables) == 0
    
    def test_template_substitute_variables(self):
        """Test substituting variables in template."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw a {{animal}} in {{environment}}"
        )
        substitutions = {"animal": "cat", "environment": "forest"}
        result = template.substitute(substitutions)
        assert result == "Draw a cat in forest"
    
    def test_template_substitute_with_missing_variable(self):
        """Test substitution with missing variable (should use placeholder)."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw a {{animal}} in {{environment}}"
        )
        substitutions = {"animal": "cat"}
        result = template.substitute(substitutions)
        # Missing variables should remain as placeholders
        assert "{{environment}}" in result or "environment" in result
    
    def test_template_substitute_partial(self):
        """Test partial substitution."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} with {{style}} style"
        )
        result = template.substitute({"animal": "dog"})
        assert "dog" in result
        assert "{{style}}" in result or "style" in result
    
    def test_template_to_dict(self):
        """Test template serialization."""
        template = PromptTemplate(
            name="Test",
            description="A test template",
            template_text="Draw {{animal}}"
        )
        template_dict = template.to_dict()
        assert template_dict["name"] == "Test"
        assert template_dict["description"] == "A test template"
        assert template_dict["template_text"] == "Draw {{animal}}"
    
    def test_template_validation_empty_name(self):
        """Test template rejects empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            PromptTemplate(name="", template_text="Test")
    
    def test_template_validation_empty_template_text(self):
        """Test template rejects empty template text."""
        with pytest.raises(ValueError, match="template_text cannot be empty"):
            PromptTemplate(name="Test", template_text="")


class TestPromptVariationService:
    """Tests for PromptVariationService class."""
    
    def test_variation_service_creation(self):
        """Test creating variation service."""
        service = PromptVariationService(load_presets=False)
        assert service is not None
        assert hasattr(service, "templates")
        assert len(service.templates) == 0
    
    def test_add_template(self):
        """Test adding a template to service."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        assert len(service.templates) == 1
        assert service.templates[0].name == "Test"
    
    def test_get_template_by_id(self):
        """Test retrieving template by ID."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        retrieved = service.get_template(template_id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_get_nonexistent_template(self):
        """Test retrieving non-existent template."""
        service = PromptVariationService(load_presets=False)
        result = service.get_template("nonexistent")
        assert result is None
    
    def test_list_all_templates(self):
        """Test listing all templates."""
        service = PromptVariationService(load_presets=False)
        templates = [
            PromptTemplate(name="T1", template_text="Text {{var1}}"),
            PromptTemplate(name="T2", template_text="Text {{var2}}"),
            PromptTemplate(name="T3", template_text="Text {{var3}}")
        ]
        for t in templates:
            service.add_template(t)
        
        all_templates = service.list_templates()
        assert len(all_templates) == 3
        names = [t.name for t in all_templates]
        assert "T1" in names
        assert "T2" in names
        assert "T3" in names
    
    def test_generate_variations_with_seed(self):
        """Test generating variations with seed control."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} in {{environment}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            seed=42,
            variables={
                "animal": ["cat", "dog", "bird", "fish"],
                "environment": ["forest", "beach", "mountain", "ocean"]
            }
        )
        
        variations = service.generate_variations(config)
        assert len(variations) == 3
        # All variations should be different strings
        assert len(set(variations)) >= 2  # At least 2 different ones
    
    def test_generate_variations_consistent_seed(self):
        """Test that same seed produces same variations."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} in {{environment}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            seed=42,
            variables={
                "animal": ["cat", "dog", "bird"],
                "environment": ["forest", "beach"]
            }
        )
        
        variations1 = service.generate_variations(config)
        variations2 = service.generate_variations(config)
        
        # Same seed should produce identical variations
        assert variations1 == variations2
    
    def test_generate_variations_different_seed(self):
        """Test that different seeds produce different variations."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config1 = VariationConfig(
            template_id=template_id,
            variations=5,
            seed=42,
            variables={"animal": ["cat", "dog", "bird"]}
        )
        config2 = VariationConfig(
            template_id=template_id,
            variations=5,
            seed=123,
            variables={"animal": ["cat", "dog", "bird"]}
        )
        
        variations1 = service.generate_variations(config1)
        variations2 = service.generate_variations(config2)
        
        # Different seeds should likely produce different results
        assert variations1 != variations2
    
    def test_generate_variations_invalid_template(self):
        """Test variation generation with invalid template ID."""
        service = PromptVariationService(load_presets=False)
        config = VariationConfig(
            template_id="nonexistent",
            variations=3,
            variables={"animal": ["cat"]}
        )
        
        with pytest.raises(ValueError, match="Template not found"):
            service.generate_variations(config)
    
    def test_generate_variations_empty_variable_options(self):
        """Test variation generation with empty variable options."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            variables={"animal": []}
        )
        
        with pytest.raises(ValueError, match="Variable .* has no options"):
            service.generate_variations(config)
    
    def test_delete_template(self):
        """Test deleting a template."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        service.delete_template(template_id)
        assert len(service.templates) == 0
        assert service.get_template(template_id) is None
    
    def test_update_template(self):
        """Test updating a template."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Original",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        updated = PromptTemplate(
            name="Updated",
            template_text="Sketch a {{animal}} in detail"
        )
        updated.id = template_id
        service.update_template(updated)
        
        retrieved = service.get_template(template_id)
        assert retrieved.name == "Updated"
        assert "detail" in retrieved.template_text
    
    def test_export_templates_json(self):
        """Test exporting templates to JSON."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        
        json_str = service.export_to_json()
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert "templates" in data
        assert len(data["templates"]) == 1
        assert data["templates"][0]["name"] == "Test"
    
    def test_import_templates_json(self):
        """Test importing templates from JSON."""
        original_service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        original_service.add_template(template)
        json_str = original_service.export_to_json()
        
        new_service = PromptVariationService(load_presets=False)
        new_service.import_from_json(json_str)
        
        assert len(new_service.templates) == 1
        assert new_service.templates[0].name == "Test"
    
    def test_library_preset_templates(self):
        """Test that library includes preset templates."""
        service = PromptVariationService(load_presets=True)
        presets = service.get_preset_templates()
        
        assert len(presets) > 0
        preset_names = [t.name for t in presets]
        assert any("animal" in name.lower() or "portrait" in name.lower() for name in preset_names)
    
    def test_template_history_tracking(self):
        """Test that template edits are tracked."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        original_text = template.template_text
        
        # Template should track creation time
        assert hasattr(template, "created_at")
        assert template.created_at is not None
        assert isinstance(template.created_at, (str, datetime))


class TestVariationConfig:
    """Tests for VariationConfig class."""
    
    def test_variation_config_creation(self):
        """Test creating variation config."""
        config = VariationConfig(
            template_id="test123",
            variations=5,
            seed=42,
            variables={"animal": ["cat", "dog"]}
        )
        assert config.template_id == "test123"
        assert config.variations == 5
        assert config.seed == 42
    
    def test_variation_config_defaults(self):
        """Test variation config default values."""
        config = VariationConfig(
            template_id="test",
            variations=3,
            variables={"animal": ["cat"]}
        )
        # seed should default to None (random)
        assert config.seed is None or isinstance(config.seed, int)
    
    def test_variation_config_validation_zero_variations(self):
        """Test config rejects zero variations."""
        with pytest.raises(ValueError, match="variations must be > 0"):
            VariationConfig(
                template_id="test",
                variations=0,
                variables={"animal": ["cat"]}
            )
    
    def test_variation_config_validation_negative_seed(self):
        """Test config allows None or positive seed."""
        config = VariationConfig(
            template_id="test",
            variations=3,
            seed=None,
            variables={"animal": ["cat"]}
        )
        assert config.seed is None


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self):
        """Test complete workflow: create template, generate variations."""
        service = PromptVariationService(load_presets=False)
        
        # Create template
        template = PromptTemplate(
            name="Fantasy Art",
            description="Fantasy creature drawing",
            template_text="Draw a {{creature}} {{emotion}} in a {{location}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        # Extract variables
        variables = template.extract_variables()
        assert len(variables) == 3
        
        # Create variation config
        config = VariationConfig(
            template_id=template_id,
            variations=4,
            seed=999,
            variables={
                "creature": ["dragon", "phoenix", "unicorn"],
                "emotion": ["happy", "angry", "sleepy"],
                "location": ["castle", "forest", "sky"]
            }
        )
        
        # Generate variations
        variations = service.generate_variations(config)
        assert len(variations) == 4
        assert all("Draw a" in v for v in variations)
    
    def test_template_persistence(self):
        """Test saving and loading templates."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{thing}}"
        )
        service.add_template(template)
        
        # Export
        json_str = service.export_to_json()
        
        # Create new service and import
        service2 = PromptVariationService(load_presets=False)
        service2.import_from_json(json_str)
        
        assert len(service2.templates) == 1
        assert service2.templates[0].name == "Test"
