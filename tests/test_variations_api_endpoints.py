"""
Tests for Variations API Endpoints (REST layer).
Tests request validation, response formatting, and error handling.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError
from src.coloring_book.api.variations_routes import (
    VariationsAPI, VariationGenerationRequest, VariationGenerationResponse
)
from src.components.prompt_template_service import (
    PromptVariationService, PromptTemplate, VariationConfig
)


class TestVariationGenerationRequest:
    """Tests for request validation."""
    
    def test_valid_request(self):
        """Test valid request creation."""
        request = VariationGenerationRequest(
            template_id="template_123",
            num_variations=5,
            variables={
                "animal": ["cat", "dog"],
                "style": ["watercolor"]
            },
            seed=42
        )
        
        assert request.template_id == "template_123"
        assert request.num_variations == 5
        assert request.seed == 42
    
    def test_request_default_num_variations(self):
        """Test default num_variations."""
        request = VariationGenerationRequest(
            template_id="template_123",
            variables={"animal": ["cat"]}
        )
        
        assert request.num_variations == 5
    
    def test_request_default_seed_none(self):
        """Test default seed is None."""
        request = VariationGenerationRequest(
            template_id="template_123",
            variables={"animal": ["cat"]}
        )
        
        assert request.seed is None
    
    def test_request_num_variations_min_boundary(self):
        """Test num_variations minimum (1)."""
        request = VariationGenerationRequest(
            template_id="template_123",
            num_variations=1,
            variables={"animal": ["cat"]}
        )
        
        assert request.num_variations == 1
    
    def test_request_num_variations_max_boundary(self):
        """Test num_variations maximum (100)."""
        request = VariationGenerationRequest(
            template_id="template_123",
            num_variations=100,
            variables={"animal": ["cat"]}
        )
        
        assert request.num_variations == 100
    
    def test_request_num_variations_below_min(self):
        """Test validation fails for num_variations < 1."""
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                num_variations=0,
                variables={"animal": ["cat"]}
            )
    
    def test_request_num_variations_above_max(self):
        """Test validation fails for num_variations > 100."""
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                num_variations=101,
                variables={"animal": ["cat"]}
            )
    
    def test_request_empty_variables(self):
        """Test validation fails for empty variables."""
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                variables={}
            )
    
    def test_request_variable_empty_options(self):
        """Test validation fails for variable with no options."""
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                variables={"animal": []}
            )
    
    def test_request_variable_options_not_list(self):
        """Test validation fails if options is not a list."""
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                variables={"animal": "cat"}
            )


class TestVariationGenerationResponse:
    """Tests for response formatting."""
    
    def test_response_creation(self):
        """Test valid response creation."""
        response = VariationGenerationResponse(
            variations=["cat", "dog"],
            template_id="template_123",
            num_variations=2,
            seed=42,
            generated_at="2024-01-01T00:00:00"
        )
        
        assert response.variations == ["cat", "dog"]
        assert response.template_id == "template_123"
        assert response.num_variations == 2
    
    def test_response_seed_none(self):
        """Test response with seed=None."""
        response = VariationGenerationResponse(
            variations=["cat"],
            template_id="template_123",
            num_variations=1,
            seed=None,
            generated_at="2024-01-01T00:00:00"
        )
        
        assert response.seed is None
    
    def test_response_to_dict(self):
        """Test response serialization to dict."""
        response = VariationGenerationResponse(
            variations=["cat", "dog"],
            template_id="template_123",
            num_variations=2,
            seed=42,
            generated_at="2024-01-01T00:00:00"
        )
        
        response_dict = response.model_dump()
        assert response_dict["variations"] == ["cat", "dog"]
        assert response_dict["template_id"] == "template_123"


class TestVariationsAPIEndpoints:
    """Tests for API endpoint handlers."""
    
    @pytest.fixture
    def service(self):
        """Create mock service."""
        return PromptVariationService(load_presets=False)
    
    @pytest.fixture
    def api(self, service):
        """Create API handler."""
        return VariationsAPI(service)
    
    @pytest.mark.asyncio
    async def test_generate_variations_success(self, api, service):
        """Test successful variation generation."""
        # Setup
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}}"
        )
        template_id = service.add_template(template)
        
        request = VariationGenerationRequest(
            template_id=template_id,
            num_variations=3,
            variables={"animal": ["cat"]},
            seed=42
        )
        
        # Execute
        result = await api.generate_variations(request)
        
        # Assert
        assert result["status"] == 200
        assert "data" in result
        assert len(result["data"]["variations"]) == 3
        assert result["data"]["seed"] == 42
    
    @pytest.mark.asyncio
    async def test_generate_variations_template_not_found(self, api):
        """Test error when template not found."""
        request = VariationGenerationRequest(
            template_id="nonexistent",
            num_variations=5,
            variables={"animal": ["cat"]}
        )
        
        result = await api.generate_variations(request)
        
        assert result["status"] == 400
        assert "error" in result
        assert "Template not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_generate_variations_empty_options_caught_by_validator(self):
        """Test that validator catches empty options before API call."""
        # The Pydantic validator should catch this
        with pytest.raises(ValidationError):
            VariationGenerationRequest(
                template_id="template_123",
                num_variations=5,
                variables={"animal": []}
            )
    
    @pytest.mark.asyncio
    async def test_generate_variations_with_seed_deterministic(self, api, service):
        """Test that API produces deterministic results with seed."""
        template = PromptTemplate(
            name="Test",
            template_text="Draw {{animal}} in {{style}}"
        )
        template_id = service.add_template(template)
        
        request = VariationGenerationRequest(
            template_id=template_id,
            num_variations=5,
            variables={
                "animal": ["cat", "dog", "bird"],
                "style": ["watercolor", "sketch"]
            },
            seed=42
        )
        
        result1 = await api.generate_variations(request)
        result2 = await api.generate_variations(request)
        
        assert result1["data"]["variations"] == result2["data"]["variations"]
    
    @pytest.mark.asyncio
    async def test_get_template_info_success(self, api, service):
        """Test getting template information."""
        template = PromptTemplate(
            name="Test Template",
            description="A test template",
            template_text="Draw {{animal}} in {{style}}"
        )
        template_id = service.add_template(template)
        
        result = await api.get_template_info(template_id)
        
        assert result["status"] == 200
        assert result["data"]["name"] == "Test Template"
        assert result["data"]["template_id"] == template_id
        assert len(result["data"]["variables"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_template_info_not_found(self, api):
        """Test error when template not found."""
        result = await api.get_template_info("nonexistent")
        
        assert result["status"] == 404
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_list_templates(self, api, service):
        """Test listing all templates."""
        # Add multiple templates
        for i in range(3):
            template = PromptTemplate(
                name=f"Template {i}",
                template_text=f"Template text {i}"
            )
            service.add_template(template)
        
        result = await api.list_templates()
        
        assert result["status"] == 200
        assert result["data"]["count"] == 3
        assert len(result["data"]["templates"]) == 3


class TestVariationsAPIValidation:
    """Tests for request validation logic."""
    
    @pytest.fixture
    def api(self):
        """Create API handler with mock service."""
        service = MagicMock()
        return VariationsAPI(service)
    
    def test_validate_request_valid(self, api):
        """Test validation of valid request."""
        request = {
            "template_id": "template_123",
            "num_variations": 5,
            "variables": {"animal": ["cat", "dog"]},
            "seed": 42
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_request_missing_template_id(self, api):
        """Test validation fails for missing template_id."""
        request = {
            "num_variations": 5,
            "variables": {"animal": ["cat"]}
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "template_id" in error
    
    def test_validate_request_missing_variables(self, api):
        """Test validation fails for missing variables."""
        request = {
            "template_id": "template_123",
            "num_variations": 5
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "variables" in error
    
    def test_validate_request_invalid_num_variations(self, api):
        """Test validation fails for invalid num_variations."""
        request = {
            "template_id": "template_123",
            "num_variations": 101,
            "variables": {"animal": ["cat"]}
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "num_variations" in error
    
    def test_validate_request_variables_not_dict(self, api):
        """Test validation fails if variables is not dict."""
        request = {
            "template_id": "template_123",
            "variables": ["animal", "cat"]
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "variables must be a dictionary" in error
    
    def test_validate_request_variable_options_not_list(self, api):
        """Test validation fails if variable options is not list."""
        request = {
            "template_id": "template_123",
            "variables": {"animal": "cat"}
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "must be a list" in error
    
    def test_validate_request_variable_empty_options(self, api):
        """Test validation fails for empty variable options."""
        request = {
            "template_id": "template_123",
            "variables": {"animal": []}
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "has no options" in error
    
    def test_validate_request_seed_not_int(self, api):
        """Test validation fails if seed is not int."""
        request = {
            "template_id": "template_123",
            "variables": {"animal": ["cat"]},
            "seed": "not_an_int"
        }
        
        is_valid, error = api.validate_request(request)
        
        assert is_valid is False
        assert "seed must be an integer" in error
