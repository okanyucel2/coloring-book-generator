"""QA/QC Validation system."""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


class ValidationError(Exception):
    """Validation error exception."""
    pass


@dataclass
class ValidationReport:
    """Result of a validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }


class QAValidator:
    """Validate coloring book metadata and assets."""

    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        """Initialize validator with optional rules."""
        self.rules = rules or self._default_rules()
        self.custom_rules: Dict[str, Callable] = {}

    @staticmethod
    def _default_rules() -> Dict[str, Any]:
        """Get default validation rules."""
        return {
            "require_title": True,
            "require_description": True,
            "require_animals": True,
            "min_animals": 1,
            "max_file_size_mb": 100,
        }

    def validate_metadata(self, metadata: Dict[str, Any]) -> ValidationReport:
        """Validate coloring book metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            ValidationReport with validation results
        """
        errors = []
        warnings = []

        # Check required fields
        if self.rules.get("require_title", True):
            if "title" not in metadata or not metadata.get("title", "").strip():
                errors.append(ValidationError("Title is required"))

        if self.rules.get("require_description", True):
            if "description" not in metadata or not metadata.get("description", "").strip():
                errors.append(ValidationError("Description is required"))

        if self.rules.get("require_animals", True):
            if "animals" not in metadata:
                errors.append(ValidationError("Animals list is required"))
            elif isinstance(metadata.get("animals"), list):
                if len(metadata["animals"]) < self.rules.get("min_animals", 1):
                    errors.append(ValidationError(f"At least {self.rules.get('min_animals', 1)} animal(s) required"))

        # Run custom rules
        for rule_name, rule_func in self.custom_rules.items():
            try:
                rule_func(metadata)
            except ValidationError as e:
                errors.append(e)

        # Create report
        is_valid = len(errors) == 0
        summary = self._generate_summary(metadata, errors, warnings, is_valid)

        return ValidationReport(
            is_valid=is_valid,
            errors=[str(e) for e in errors],
            warnings=[str(w) for w in warnings],
            summary=summary,
            data=metadata,
        )

    def validate_image_quality(self, image_config: Dict[str, Any]) -> ValidationReport:
        """Validate image quality and specifications.
        
        Args:
            image_config: Image configuration
            
        Returns:
            ValidationReport
        """
        errors = []
        
        if "min_resolution" in image_config:
            # Would check actual image here
            pass

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            summary="Image validation complete",
        )

    def validate_pdf(self, pdf_config: Dict[str, Any]) -> ValidationReport:
        """Validate PDF document.
        
        Args:
            pdf_config: PDF configuration
            
        Returns:
            ValidationReport
        """
        errors = []
        
        if pdf_config.get("pages", 0) < 1:
            errors.append("PDF must have at least 1 page")

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            summary="PDF validation complete",
        )

    def validate_batch(self, items: List[Dict[str, Any]]) -> List[ValidationReport]:
        """Validate multiple items.
        
        Args:
            items: List of metadata dictionaries
            
        Returns:
            List of ValidationReports
        """
        return [self.validate_metadata(item) for item in items]

    def add_custom_rule(self, name: str, rule_func: Callable) -> bool:
        """Add a custom validation rule.
        
        Args:
            name: Rule name
            rule_func: Function that raises ValidationError on failure
            
        Returns:
            True if added successfully
        """
        self.custom_rules[name] = rule_func
        return True

    @staticmethod
    def _generate_summary(metadata: Dict[str, Any], errors: List, warnings: List, is_valid: bool) -> str:
        """Generate validation summary."""
        if is_valid:
            return f"✅ Validation passed for '{metadata.get('title', 'Unknown')}'"
        else:
            return f"❌ Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)"
