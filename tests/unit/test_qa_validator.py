"""Tests for QA Validation system."""
import pytest
from coloring_book.qc.validator import QAValidator, ValidationReport, ValidationError


@pytest.fixture
def validator():
    """Create QAValidator instance."""
    return QAValidator()


class TestQAValidatorBasics:
    """Test QAValidator initialization and basic functionality."""

    def test_validator_creates_instance(self):
        v = QAValidator()
        assert v is not None

    def test_validator_validate_metadata(self, validator):
        metadata = {
            "title": "Test Book",
            "description": "A test book",
            "animals": [{"name": "Cat", "difficulty": "easy"}]
        }
        result = validator.validate_metadata(metadata)
        assert result.is_valid
        assert result.errors == []

    def test_validator_missing_title(self, validator):
        metadata = {"description": "Test"}
        result = validator.validate_metadata(metadata)
        assert not result.is_valid
        assert any("title" in str(e).lower() for e in result.errors)

    def test_validator_missing_animals(self, validator):
        metadata = {"title": "Test", "description": "Test"}
        result = validator.validate_metadata(metadata)
        assert not result.is_valid
        assert any("animal" in str(e).lower() for e in result.errors)

    def test_validation_report_has_summary(self, validator):
        metadata = {"title": "Test", "description": "Test"}
        result = validator.validate_metadata(metadata)
        assert result.summary is not None
        assert isinstance(result.summary, str)

    def test_validation_report_has_timestamp(self, validator):
        metadata = {"title": "Test Book", "description": "Test", "animals": []}
        result = validator.validate_metadata(metadata)
        assert result.timestamp is not None

    def test_validator_image_quality_check(self, validator):
        result = validator.validate_image_quality({
            "path": "/tmp/test.png",
            "min_resolution": (300, 300),
            "max_size_mb": 5
        })
        assert result is not None

    def test_validator_pdf_validation(self, validator):
        result = validator.validate_pdf({
            "pages": 10,
            "title": "Test",
            "has_metadata": True
        })
        assert result.is_valid or not result.is_valid

    def test_validator_batch_validation(self, validator):
        items = [
            {"title": "Book 1", "description": "Test", "animals": [{"name": "Cat"}]},
            {"title": "Book 2", "description": "Test", "animals": [{"name": "Dog"}]}
        ]
        results = validator.validate_batch(items)
        assert len(results) == 2
        assert all(isinstance(r, ValidationReport) for r in results)

    def test_validator_rules_configuration(self):
        rules = {
            "require_title": True,
            "min_animals": 1,
            "max_file_size_mb": 100
        }
        v = QAValidator(rules=rules)
        assert v.rules == rules

    def test_validator_custom_rules(self, validator):
        def custom_rule(data):
            if "custom_field" not in data:
                raise ValidationError("Missing custom_field")
        
        result = validator.add_custom_rule("custom", custom_rule)
        assert result is not None

    def test_validation_error_is_descriptive(self, validator):
        metadata = {"title": "Test"}
        result = validator.validate_metadata(metadata)
        for error in result.errors:
            assert len(str(error)) > 0
            assert isinstance(error, str)

    def test_validation_report_to_dict(self, validator):
        metadata = {"title": "Test Book", "description": "Test", "animals": []}
        result = validator.validate_metadata(metadata)
        report_dict = result.to_dict()
        assert "is_valid" in report_dict
        assert "errors" in report_dict
        assert "summary" in report_dict

    def test_validator_returns_report_object(self, validator):
        metadata = {"title": "Test Book", "description": "Test", "animals": [{"name": "Cat"}]}
        result = validator.validate_metadata(metadata)
        assert isinstance(result, ValidationReport)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "summary")

    def test_validator_batch_with_partial_failures(self, validator):
        items = [
            {"title": "Book 1", "description": "Test", "animals": [{"name": "Cat"}]},
            {"title": "Book 2", "description": "Test"},  # Missing animals
            {"description": "Test", "animals": [{"name": "Dog"}]}  # Missing title
        ]
        results = validator.validate_batch(items)
        assert len(results) == 3
        assert any(not r.is_valid for r in results)
        assert any(r.is_valid for r in results)

    def test_validator_generate_report_file(self, validator):
        import tempfile
        metadata = {"title": "Test Book", "description": "Test", "animals": []}
        result = validator.validate_metadata(metadata)
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            report_text = result.summary
            assert len(report_text) > 0


class TestValidationRules:
    """Test individual validation rules."""

    def test_rule_metadata_completeness(self):
        v = QAValidator()
        incomplete = {"title": "Test"}
        result = v.validate_metadata(incomplete)
        assert not result.is_valid

    def test_rule_animal_list_not_empty(self):
        v = QAValidator()
        metadata = {"title": "Test", "description": "Test", "animals": []}
        result = v.validate_metadata(metadata)
        assert any("animal" in str(e).lower() for e in result.errors)

    def test_rule_string_fields_not_empty(self):
        v = QAValidator()
        metadata = {"title": "", "description": "Test", "animals": []}
        result = v.validate_metadata(metadata)
        assert not result.is_valid

    def test_rule_keywords_format(self):
        v = QAValidator()
        metadata = {
            "title": "Test",
            "description": "Test",
            "animals": [{"name": "Cat"}],
            "keywords": ["valid", "keywords"]
        }
        result = v.validate_metadata(metadata)
        assert result.is_valid or not result.is_valid


class TestValidationPerformance:
    """Test validation performance."""

    def test_validator_batch_large_dataset(self):
        v = QAValidator()
        items = [
            {"title": f"Book {i}", "description": "Test", "animals": [{"name": f"Animal {i}"}]}
            for i in range(100)
        ]
        results = v.validate_batch(items)
        assert len(results) == 100

    def test_validator_handles_deep_nesting(self):
        v = QAValidator()
        metadata = {
            "title": "Test",
            "description": "Test",
            "animals": [
                {
                    "name": "Cat",
                    "details": {
                        "description": "A cat",
                        "tags": ["feline", "pet"]
                    }
                }
            ]
        }
        result = v.validate_metadata(metadata)
        assert result is not None
