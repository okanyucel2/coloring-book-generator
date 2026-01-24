"""Edge case and comprehensive coverage tests for PromptTemplateService."""

import pytest
import json
from src.components.prompt_template_service import (
    PromptTemplate,
    PromptVariationService,
    VariationConfig,
)


class TestEdgeCases:
    """Edge case tests for full code coverage."""
    
    def test_template_is_preset_flag(self):
        """Test is_preset flag tracking."""
        preset_template = PromptTemplate(
            name="Preset",
            template_text="Draw {{animal}}",
            is_preset=True
        )
        user_template = PromptTemplate(
            name="User",
            template_text="Draw {{animal}}",
            is_preset=False
        )
        
        assert preset_template.is_preset is True
        assert user_template.is_preset is False
        
        preset_dict = preset_template.to_dict()
        assert preset_dict["is_preset"] is True
    
    def test_service_with_preset_loading_disabled(self):
        """Test service initialization without presets."""
        service = PromptVariationService(load_presets=False)
        assert len(service.templates) == 0
        
        presets = service.get_preset_templates()
        assert len(presets) == 0
    
    def test_service_with_preset_loading_enabled(self):
        """Test service initialization with presets."""
        service = PromptVariationService(load_presets=True)
        assert len(service.templates) > 0
        
        presets = service.get_preset_templates()
        assert len(presets) > 0
        assert all(t.is_preset for t in presets)
    
    def test_import_json_invalid_format(self):
        """Test import with invalid JSON format."""
        service = PromptVariationService(load_presets=False)
        
        with pytest.raises(ValueError, match="Invalid JSON format"):
            service.import_from_json("not valid json {")
    
    def test_import_json_missing_required_field(self):
        """Test import with missing required template field."""
        service = PromptVariationService(load_presets=False)
        invalid_json = json.dumps({
            "templates": [
                {"name": "Test"}  # Missing template_text
            ]
        })
        
        with pytest.raises(ValueError, match="Invalid JSON format"):
            service.import_from_json(invalid_json)
    
    def test_generate_variations_with_unspecified_variables(self):
        """Test variations generation fills missing variables with 'default'."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} in {{environment}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        # Only provide one variable, not both
        config = VariationConfig(
            template_id=template_id,
            variations=2,
            seed=42,
            variables={"animal": ["cat", "dog"]}
            # missing "environment"
        )
        
        variations = service.generate_variations(config)
        assert len(variations) == 2
        # Missing variable should be replaced with "default"
        assert all("default" in v for v in variations)
    
    def test_template_substitute_with_numeric_values(self):
        """Test substitution with non-string values."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{count}} animals"
        )
        result = template.substitute({"count": 5})
        assert result == "Draw 5 animals"
    
    def test_template_substitute_with_special_characters(self):
        """Test substitution with special regex characters."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{style}} animal"
        )
        result = template.substitute({"style": "(.+) regex"})
        assert "(.+) regex" in result
    
    def test_export_and_import_with_tags(self):
        """Test that tags are preserved during export/import."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Tagged",
            template_text="Draw {{animal}}",
            tags=["animal", "portrait", "sketch"]
        )
        service.add_template(template)
        
        json_str = service.export_to_json()
        
        service2 = PromptVariationService(load_presets=False)
        service2.import_from_json(json_str)
        
        assert service2.templates[0].tags == ["animal", "portrait", "sketch"]
    
    def test_export_preserves_template_id(self):
        """Test that template IDs are preserved during export/import."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        original_id = template.id
        
        json_str = service.export_to_json()
        
        service2 = PromptVariationService(load_presets=False)
        service2.import_from_json(json_str)
        
        assert service2.templates[0].id == original_id
    
    def test_generate_variations_with_single_option(self):
        """Test variations with only one option per variable."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=5,
            variables={"animal": ["cat"]}
        )
        
        variations = service.generate_variations(config)
        # All variations should be identical (only one option)
        assert len(set(variations)) == 1
        assert all("cat" in v for v in variations)
    
    def test_generate_variations_with_many_variables(self):
        """Test variations with many variables."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Complex",
            template_text="Draw a {{color}} {{animal}} {{emotion}} in {{location}} with {{style}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=10,
            seed=42,
            variables={
                "color": ["red", "blue"],
                "animal": ["cat", "dog"],
                "emotion": ["happy", "sad"],
                "location": ["forest", "city"],
                "style": ["watercolor", "sketch"]
            }
        )
        
        variations = service.generate_variations(config)
        assert len(variations) == 10
        assert all("Draw a" in v for v in variations)
    
    def test_extract_variables_with_underscores_and_numbers(self):
        """Test variable extraction with underscores and numbers."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal_type}} and {{color_1}} and {{size_2}}"
        )
        variables = template.extract_variables()
        var_names = [v.name for v in variables]
        
        assert "animal_type" in var_names
        assert "color_1" in var_names
        assert "size_2" in var_names
        assert len(variables) == 3
    
    def test_extract_variables_ignores_invalid_patterns(self):
        """Test that invalid variable patterns are ignored."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{valid}} and {{ spaces }} and {{-invalid}} and {{}}"
        )
        variables = template.extract_variables()
        var_names = [v.name for v in variables]
        
        assert "valid" in var_names
        # Invalid patterns should not be extracted
        assert len(variables) == 1
    
    def test_delete_nonexistent_template(self):
        """Test deleting template that doesn't exist (should be no-op)."""
        service = PromptVariationService(load_presets=False)
        service.delete_template("nonexistent")
        assert len(service.templates) == 0
    
    def test_update_nonexistent_template(self):
        """Test updating template that doesn't exist."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        
        with pytest.raises(ValueError, match="not found"):
            service.update_template(template)
    
    def test_template_whitespace_trimming(self):
        """Test that template names and text are trimmed."""
        template = PromptTemplate(
            name="  Test  ",
            template_text="  Draw {{animal}}  "
        )
        
        assert template.name == "Test"
        assert template.template_text == "Draw {{animal}}"
    
    def test_variation_config_with_negative_seed(self):
        """Test that negative seeds are allowed (valid in Python random)."""
        config = VariationConfig(
            template_id="test",
            variations=3,
            seed=-42,
            variables={"animal": ["cat"]}
        )
        assert config.seed == -42
    
    def test_generate_variations_maintains_order(self):
        """Test that seed produces consistent ordering across calls."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="{{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        config = VariationConfig(
            template_id=template_id,
            variations=3,
            seed=12345,
            variables={"animal": ["a", "b", "c", "d", "e"]}
        )
        
        variations1 = service.generate_variations(config)
        variations2 = service.generate_variations(config)
        
        # Exact same order
        assert variations1 == variations2


class TestErrorHandling:
    """Tests for error handling and defensive programming."""
    
    def test_generate_variations_all_variables_required(self):
        """Test that generation validates all required variables."""
        service = PromptVariationService(load_presets=False)
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        service.add_template(template)
        template_id = service.templates[0].id
        
        # Config with missing 'animal' variable
        config = VariationConfig(
            template_id=template_id,
            variations=2,
            variables={}
        )
        
        # Should fill with 'default'
        variations = service.generate_variations(config)
        assert len(variations) == 2
        assert all("default" in v for v in variations)
    
    def test_template_variable_extraction_case_sensitive(self):
        """Test that variable names are case-sensitive."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{Animal}} and {{animal}}"
        )
        variables = template.extract_variables()
        var_names = [v.name for v in variables]
        
        # Both should be extracted as different variables
        assert "Animal" in var_names
        assert "animal" in var_names
        assert len(variables) == 2
    
    def test_export_empty_templates_list(self):
        """Test exporting service with no templates."""
        service = PromptVariationService(load_presets=False)
        json_str = service.export_to_json()
        data = json.loads(json_str)
        
        assert data["templates"] == []
        assert "exported_at" in data


class TestDataPersistence:
    """Tests for data persistence and serialization."""
    
    def test_template_preserves_all_fields_in_serialization(self):
        """Test that all template fields are preserved during serialization."""
        template = PromptTemplate(
            name="Complete",
            template_text="Draw {{animal}}",
            description="A complete template",
            tags=["animal", "drawing"]
        )
        
        # Manually set timestamps for consistency
        import datetime
        now = datetime.datetime.now().isoformat()
        template.created_at = now
        template.updated_at = now
        
        template_dict = template.to_dict()
        
        # Verify all fields present
        assert template_dict["id"] == template.id
        assert template_dict["name"] == "Complete"
        assert template_dict["template_text"] == "Draw {{animal}}"
        assert template_dict["description"] == "A complete template"
        assert template_dict["tags"] == ["animal", "drawing"]
        assert template_dict["created_at"] == now
        assert template_dict["updated_at"] == now
        assert template_dict["is_preset"] is False
    
    def test_import_preserves_all_fields(self):
        """Test that all fields are preserved during import/export cycle."""
        service = PromptVariationService(load_presets=False)
        original = PromptTemplate(
            name="Original",
            template_text="Draw {{animal}} in {{environment}}",
            description="Test template for preservation",
            tags=["test", "preserve"]
        )
        service.add_template(original)
        
        # Export and reimport
        json_str = service.export_to_json()
        service2 = PromptVariationService(load_presets=False)
        service2.import_from_json(json_str)
        
        reimported = service2.templates[0]
        assert reimported.name == original.name
        assert reimported.template_text == original.template_text
        assert reimported.description == original.description
        assert reimported.tags == original.tags
        assert reimported.id == original.id
