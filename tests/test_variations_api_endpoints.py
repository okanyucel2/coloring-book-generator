"""
Tests for Variations API Endpoints (REST layer) - REFACTORED v2
Tests request validation, response formatting, and error handling.

Refactored to:
- Remove redundant validate_request() tests (Pydantic handles validation)
- Test new error handling architecture with custom exceptions
- Verify error classification (ValueError → 400, TemplateNotFoundError → 404)
- Add comprehensive error handler tests
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError
from src.coloring_book.api.variations_routes import (
    VariationsAPI, VariationGenerationRequest, VariationGenerationResponse,
    TemplateNotFoundError
)
from src.components.prompt_template_service import (
    PromptVariationService, PromptTemplate, VariationConfig
)


class TestVariationGenerationRequest:
    """Tests for request validation via Pydantic."""
    
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
        """Test error when template not found (400 from service ValueError)."""
        request = VariationGenerationRequest(
            template_id="nonexistent",
            num_variations=5,
            variables={"animal": ["cat"]}
        )
        
        result = await api.generate_variations(request)
        
        # PromptVariationService.generate_variations raises ValueError
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
        """Test error when template not found (404 from TemplateNotFoundError)."""
        result = await api.get_template_info("nonexistent")
        
        assert result["status"] == 404
        assert "error" in result
        assert "not found" in result["error"].lower()
    
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


class TestErrorHandling:
    """Tests for error handling mechanism with custom exceptions."""
    
    def test_handle_error_success_operation(self):
        """Test _handle_error with successful operation."""
        def operation():
            return {"data": {"key": "value"}}
        
        result = VariationsAPI._handle_error(operation)
        
        assert result["status"] == 200
        assert result["data"]["key"] == "value"
    
    def test_handle_error_custom_status(self):
        """Test _handle_error with custom success status."""
        def operation():
            return {"data": {"key": "value"}}
        
        result = VariationsAPI._handle_error(operation, status_ok=201)
        
        assert result["status"] == 201
        assert result["data"]["key"] == "value"
    
    def test_handle_error_value_error_default_mapping(self):
        """Test _handle_error with ValueError (default error_map)."""
        def operation():
            raise ValueError("Invalid input")
        
        result = VariationsAPI._handle_error(operation)
        
        assert result["status"] == 400
        assert "Invalid input" in result["error"]
    
    def test_handle_error_template_not_found_default_mapping(self):
        """Test _handle_error with TemplateNotFoundError (default error_map)."""
        def operation():
            raise TemplateNotFoundError("Template not found: xyz")
        
        result = VariationsAPI._handle_error(operation)
        
        assert result["status"] == 404
        assert "Template not found" in result["error"]
    
    def test_handle_error_generic_exception_default_mapping(self):
        """Test _handle_error with unmapped exception (default → 500)."""
        def operation():
            raise RuntimeError("Unexpected error")
        
        result = VariationsAPI._handle_error(operation)
        
        assert result["status"] == 500
        assert "Internal server error" in result["error"]
    
    def test_handle_error_custom_error_map(self):
        """Test _handle_error with custom error mapping."""
        class CustomError(Exception):
            pass
        
        def operation():
            raise CustomError("Custom problem")
        
        custom_map = {CustomError: 418}  # I'm a teapot
        result = VariationsAPI._handle_error(operation, error_map=custom_map)
        
        assert result["status"] == 418
        assert "Custom problem" in result["error"]
    
    def test_handle_error_preserves_exception_message(self):
        """Test that error handler preserves exception messages."""
        def operation():
            raise ValueError("Specific validation issue")
        
        result = VariationsAPI._handle_error(operation)
        
        # Message should be preserved without modification
        assert result["error"] == "Specific validation issue"
    
    def test_handle_error_enhances_generic_500_messages(self):
        """Test that generic 500 errors get enhanced messages."""
        def operation():
            raise RuntimeError("Database connection failed")
        
        result = VariationsAPI._handle_error(operation)
        
        assert result["status"] == 500
        # Message should be enhanced for generic exceptions
        assert "Internal server error" in result["error"]
        assert "Database connection failed" in result["error"]
