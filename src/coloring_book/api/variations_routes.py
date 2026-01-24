"""
Variation Generation API Routes (REFACTORED v2)
FastAPI endpoints for prompt template variation generation with seed control.

Improvements applied:
- Removed redundant validate_request() method (Pydantic handles validation)
- Extracted error handling to helper method (DRY principle)
- Consistent error handling pattern throughout
- Better error classification (use custom exceptions, not ValueError)
- Async/await maintained for FastAPI compatibility
- Cleaner, more maintainable code structure
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from src.components.prompt_template_service import (
    PromptVariationService, VariationConfig
)


# Custom exceptions for better error classification
class TemplateNotFoundError(Exception):
    """Raised when template cannot be found."""
    pass


class VariationGenerationRequest(BaseModel):
    """Request model for variation generation."""
    template_id: str = Field(..., description="ID of the template to use")
    num_variations: int = Field(
        default=5, 
        ge=1, 
        le=100,
        description="Number of variations to generate (1-100)"
    )
    variables: Dict[str, List[str]] = Field(
        ..., 
        description="Variable options: {var_name: [option1, option2, ...]}"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for deterministic generation (optional)"
    )
    
    @field_validator('variables')
    @classmethod
    def validate_variables(cls, v):
        """Validate variables dictionary."""
        if not v:
            raise ValueError("variables cannot be empty")
        
        for var_name, options in v.items():
            if not isinstance(options, list):
                raise ValueError(f"Variable '{var_name}' options must be a list")
            if len(options) == 0:
                raise ValueError(f"Variable '{var_name}' has no options")
        
        return v


class VariationGenerationResponse(BaseModel):
    """Response model for variation generation."""
    variations: List[str] = Field(..., description="Generated variations")
    template_id: str = Field(..., description="Template ID used")
    num_variations: int = Field(..., description="Number of variations generated")
    seed: Optional[int] = Field(..., description="Seed used (if provided)")
    generated_at: str = Field(..., description="Generation timestamp")


class VariationsAPI:
    """Handler for variation generation API endpoints (REFACTORED v2)."""
    
    def __init__(self, service: PromptVariationService):
        """
        Initialize variations API.
        
        Args:
            service: PromptVariationService instance
        """
        self.service = service
    
    @staticmethod
    def _handle_error(operation: Callable[[], Dict], 
                     status_ok: int = 200,
                     error_map: Optional[Dict[type, int]] = None) -> Dict:
        """
        Generic error handler for API operations (extracted for DRY principle).
        
        Handles exception → HTTP status code mapping.
        
        Args:
            operation: Callable that returns dict (success case)
            status_ok: HTTP status for success (default: 200)
            error_map: Dict mapping exception type → HTTP status code
                      Default: {ValueError: 400, TemplateNotFoundError: 404}
        
        Returns:
            Dict with status and data/error fields
        
        Example:
            result = VariationsAPI._handle_error(
                lambda: {"data": fetch_template()},
                error_map={TemplateNotFoundError: 404, ValueError: 400}
            )
        """
        if error_map is None:
            error_map = {
                TemplateNotFoundError: 404,
                ValueError: 400
            }
        
        try:
            result = operation()
            if "status" not in result:
                result["status"] = status_ok
            return result
        except Exception as e:
            # Determine status code from error type mapping
            status = error_map.get(type(e), 500)
            error_msg = str(e)
            
            # Enhance error message for generic 500 errors
            if status == 500 and not error_msg.startswith("Internal"):
                error_msg = f"Internal server error: {error_msg}"
            
            return {"status": status, "error": error_msg}
    
    async def generate_variations(self, request: VariationGenerationRequest) -> Dict:
        """
        Generate prompt variations with optional seed control.
        
        Args:
            request: VariationGenerationRequest containing template_id, variables, seed
        
        Returns:
            Dict with generated variations and metadata
            
        Raises:
            ValueError: If validation fails (caught and returned as 400)
            TemplateNotFoundError: If template doesn't exist (caught and returned as 404)
        """
        def operation():
            # Create configuration
            config = VariationConfig(
                template_id=request.template_id,
                variations=request.num_variations,
                variables=request.variables,
                seed=request.seed
            )
            
            # Generate variations (raises ValueError if template not found)
            variations = self.service.generate_variations(config)
            
            # Build response
            response = VariationGenerationResponse(
                variations=variations,
                template_id=request.template_id,
                num_variations=len(variations),
                seed=request.seed,
                generated_at=datetime.now(timezone.utc).isoformat()
            )
            
            return {"data": response.model_dump()}
        
        return self._handle_error(operation)
    
    async def get_template_info(self, template_id: str) -> Dict:
        """
        Get template information for variation generation.
        
        Args:
            template_id: Template ID
        
        Returns:
            Dict with template info and variables
            
        Raises:
            TemplateNotFoundError: If template doesn't exist (caught and returned as 404)
        """
        def operation():
            template = self.service.get_template(template_id)
            
            if not template:
                raise TemplateNotFoundError(f"Template not found: {template_id}")
            
            variables = template.extract_variables()
            
            return {
                "data": {
                    "template_id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "template_text": template.template_text,
                    "variables": [
                        {
                            "name": var.name,
                            "description": var.description,
                            "default_value": var.default_value,
                            "required": var.required
                        }
                        for var in variables
                    ]
                }
            }
        
        return self._handle_error(operation)
    
    async def list_templates(self) -> Dict:
        """
        List all available templates.
        
        Returns:
            Dict with list of templates
        """
        def operation():
            templates = self.service.list_templates()
            
            return {
                "data": {
                    "templates": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "description": t.description,
                            "is_preset": t.is_preset,
                            "created_at": t.created_at
                        }
                        for t in templates
                    ],
                    "count": len(templates)
                }
            }
        
        return self._handle_error(operation)
