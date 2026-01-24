"""
Variation Generation API Routes
FastAPI endpoints for prompt template variation generation with seed control.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from src.components.prompt_template_service import (
    PromptVariationService, VariationConfig
)


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
    """Handler for variation generation API endpoints."""
    
    def __init__(self, service: PromptVariationService):
        """
        Initialize variations API.
        
        Args:
            service: PromptVariationService instance
        """
        self.service = service
    
    async def generate_variations(self, request: VariationGenerationRequest) -> Dict:
        """
        Generate prompt variations with optional seed control.
        
        Args:
            request: VariationGenerationRequest containing template_id, variables, seed
        
        Returns:
            Dict with generated variations and metadata
        
        Raises:
            ValueError: If template not found or config invalid
        """
        try:
            # Create configuration
            config = VariationConfig(
                template_id=request.template_id,
                variations=request.num_variations,
                variables=request.variables,
                seed=request.seed
            )
            
            # Generate variations
            variations = self.service.generate_variations(config)
            
            # Build response
            response = VariationGenerationResponse(
                variations=variations,
                template_id=request.template_id,
                num_variations=len(variations),
                seed=request.seed,
                generated_at=datetime.now(timezone.utc).isoformat()
            )
            
            return {
                "status": 200,
                "data": response.model_dump()
            }
        
        except ValueError as e:
            return {
                "status": 400,
                "error": str(e)
            }
        except Exception as e:
            return {
                "status": 500,
                "error": f"Internal server error: {str(e)}"
            }
    
    async def get_template_info(self, template_id: str) -> Dict:
        """
        Get template information for variation generation.
        
        Args:
            template_id: Template ID
        
        Returns:
            Dict with template info and variables
        """
        try:
            template = self.service.get_template(template_id)
            
            if not template:
                return {
                    "status": 404,
                    "error": f"Template not found: {template_id}"
                }
            
            variables = template.extract_variables()
            
            return {
                "status": 200,
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
        
        except Exception as e:
            return {
                "status": 500,
                "error": f"Internal server error: {str(e)}"
            }
    
    async def list_templates(self) -> Dict:
        """
        List all available templates.
        
        Returns:
            Dict with list of templates
        """
        try:
            templates = self.service.list_templates()
            
            return {
                "status": 200,
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
        
        except Exception as e:
            return {
                "status": 500,
                "error": f"Internal server error: {str(e)}"
            }
    
    def validate_request(self, request_dict: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate variation generation request.
        
        Args:
            request_dict: Request dictionary
        
        Returns:
            (is_valid, error_message) tuple
        """
        # Check required fields
        if "template_id" not in request_dict:
            return False, "Missing required field: template_id"
        
        if "variables" not in request_dict:
            return False, "Missing required field: variables"
        
        # Validate num_variations
        num_variations = request_dict.get("num_variations", 5)
        if not isinstance(num_variations, int) or num_variations < 1 or num_variations > 100:
            return False, "num_variations must be integer between 1 and 100"
        
        # Validate variables format
        variables = request_dict.get("variables")
        if not isinstance(variables, dict):
            return False, "variables must be a dictionary"
        
        for var_name, options in variables.items():
            if not isinstance(options, list):
                return False, f"Variable '{var_name}' options must be a list"
            if len(options) == 0:
                return False, f"Variable '{var_name}' has no options"
        
        # Validate seed if provided
        seed = request_dict.get("seed")
        if seed is not None and not isinstance(seed, int):
            return False, "seed must be an integer or null"
        
        return True, None
