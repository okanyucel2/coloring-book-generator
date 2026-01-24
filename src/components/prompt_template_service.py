"""
Prompt Template and Variation Generation Service.
Allows users to create custom prompt templates with variables,
and generate multiple variations with configurable seed control.
"""

import uuid
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set
from datetime import datetime
import random


@dataclass
class PromptVariable:
    """Represents a variable in a prompt template."""
    name: str
    description: str = ""
    default_value: Optional[str] = None
    required: bool = False
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class PromptTemplate:
    """Represents a reusable prompt template with variables."""
    name: str
    template_text: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    is_preset: bool = False  # Track if this is a preset template
    
    def __post_init__(self):
        """Validate template on creation."""
        if not self.name or not self.name.strip():
            raise ValueError("Template name cannot be empty")
        if not self.template_text or not self.template_text.strip():
            raise ValueError("Template template_text cannot be empty")
        self.name = self.name.strip()
        self.template_text = self.template_text.strip()
    
    def extract_variables(self) -> List[PromptVariable]:
        """Extract all {{variable}} placeholders from template text.
        
        Returns:
            List of PromptVariable objects (no duplicates).
        """
        # Find all {{variable}} patterns
        pattern = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'
        matches = re.findall(pattern, self.template_text)
        
        # Remove duplicates while preserving order
        seen = set()
        variables = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                variables.append(PromptVariable(name=match))
        
        return variables
    
    def substitute(self, substitutions: Dict[str, str]) -> str:
        """Replace {{variable}} placeholders with provided values.
        
        Args:
            substitutions: Dict mapping variable names to replacement values.
                          Missing variables remain as {{variable}}.
        
        Returns:
            Template text with substitutions applied.
        """
        result = self.template_text
        
        # Replace each {{variable}} with its substitution
        for var_name, value in substitutions.items():
            pattern = r'\{\{' + var_name + r'\}\}'
            result = re.sub(pattern, str(value), result)
        
        return result
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_text": self.template_text,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "is_preset": self.is_preset
        }


@dataclass
class VariationConfig:
    """Configuration for generating prompt variations."""
    template_id: str
    variations: int
    variables: Dict[str, List[str]]  # var_name -> list of options
    seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.variations <= 0:
            raise ValueError("variations must be > 0")
        
        # Note: Don't validate variable options here - validate during generation
        # This allows lazy validation and better error messages


class PromptVariationService:
    """Service for managing prompt templates and generating variations."""
    
    def __init__(self, load_presets: bool = True):
        """Initialize service.
        
        Args:
            load_presets: If True, load preset templates on initialization.
                         Set to False for testing to have empty service.
        """
        self.templates: List[PromptTemplate] = []
        if load_presets:
            self._load_preset_templates()
    
    def _load_preset_templates(self):
        """Load preset templates into the service."""
        presets = [
            PromptTemplate(
                name="Animal Portrait",
                template_text="Draw a detailed {{animal}} portrait in {{style}} style",
                description="Create portraits of different animals with various artistic styles",
                tags=["animal", "portrait", "style"],
                is_preset=True
            ),
            PromptTemplate(
                name="Fantasy Scene",
                template_text="Create a {{emotion}} fantasy scene with {{creature}} in {{location}}",
                description="Generate fantasy artwork with creatures and environments",
                tags=["fantasy", "scene", "creature"],
                is_preset=True
            ),
            PromptTemplate(
                name="Nature Study",
                template_text="Draw a {{plant_or_flower}} in {{season}}, {{artistic_technique}}",
                description="Create nature studies with different plants and seasons",
                tags=["nature", "botanical", "seasonal"],
                is_preset=True
            ),
        ]
        for preset in presets:
            self.templates.append(preset)
    
    def add_template(self, template: PromptTemplate) -> str:
        """Add a new template to the service.
        
        Args:
            template: PromptTemplate object.
        
        Returns:
            Template ID.
        """
        self.templates.append(template)
        return template.id
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Retrieve a template by ID.
        
        Args:
            template_id: Template ID.
        
        Returns:
            PromptTemplate or None if not found.
        """
        for template in self.templates:
            if template.id == template_id:
                return template
        return None
    
    def list_templates(self) -> List[PromptTemplate]:
        """List all available templates.
        
        Returns:
            List of all templates.
        """
        return self.templates.copy()
    
    def update_template(self, template: PromptTemplate) -> None:
        """Update an existing template.
        
        Args:
            template: Updated PromptTemplate object (must have existing ID).
        
        Raises:
            ValueError: If template ID not found.
        """
        for i, t in enumerate(self.templates):
            if t.id == template.id:
                template.updated_at = datetime.now().isoformat()
                self.templates[i] = template
                return
        raise ValueError(f"Template '{template.id}' not found")
    
    def delete_template(self, template_id: str) -> None:
        """Delete a template by ID.
        
        Args:
            template_id: Template ID to delete.
        """
        self.templates = [t for t in self.templates if t.id != template_id]
    
    def generate_variations(self, config: VariationConfig) -> List[str]:
        """Generate prompt variations from a template.
        
        Args:
            config: VariationConfig specifying template, variable options, seed.
        
        Returns:
            List of generated prompts.
        
        Raises:
            ValueError: If template not found or config invalid.
        """
        # Validate template exists
        template = self.get_template(config.template_id)
        if template is None:
            raise ValueError(f"Template not found: {config.template_id}")
        
        # Validate all variables have options (defensive check)
        for var_name, options in config.variables.items():
            if not isinstance(options, (list, tuple)) or len(options) == 0:
                raise ValueError(f"Variable '{var_name}' has no options")
        
        # Set random seed if provided
        if config.seed is not None:
            random.seed(config.seed)
        
        # Defensive: add default values for template variables not in config
        template_vars = {v.name for v in template.extract_variables()}
        for var_name in template_vars:
            if var_name not in config.variables:
                config.variables[var_name] = ["default"]
        
        # Generate variations
        variations = []
        for _ in range(config.variations):
            substitutions = {}
            for var_name, options in config.variables.items():
                # Randomly select from options
                substitutions[var_name] = random.choice(options)
            
            # Apply substitution to template
            prompt = template.substitute(substitutions)
            variations.append(prompt)
        
        return variations
    
    def export_to_json(self) -> str:
        """Export all templates to JSON string.
        
        Returns:
            JSON string containing all templates.
        """
        data = {
            "templates": [t.to_dict() for t in self.templates],
            "exported_at": datetime.now().isoformat()
        }
        return json.dumps(data, indent=2)
    
    def import_from_json(self, json_str: str) -> int:
        """Import templates from JSON string.
        
        Args:
            json_str: JSON string containing template data.
        
        Returns:
            Number of templates imported.
        
        Raises:
            ValueError: If JSON is invalid.
        """
        try:
            data = json.loads(json_str)
            count = 0
            for template_data in data.get("templates", []):
                template = PromptTemplate(
                    name=template_data["name"],
                    template_text=template_data["template_text"],
                    description=template_data.get("description", ""),
                    id=template_data.get("id", str(uuid.uuid4())),
                    tags=template_data.get("tags", []),
                    is_preset=template_data.get("is_preset", False)
                )
                self.templates.append(template)
                count += 1
            return count
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
    
    def get_preset_templates(self) -> List[PromptTemplate]:
        """Get only the preset templates (non-user-created).
        
        Returns:
            List of preset templates.
        """
        return [t for t in self.templates if t.is_preset]
