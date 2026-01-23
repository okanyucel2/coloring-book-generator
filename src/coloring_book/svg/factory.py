"""Animal factory for creating drawer instances."""

from typing import Optional, Dict, Any
from .base import AnimalDrawer
from .registry import AnimalRegistry


class AnimalFactory:
    """Factory for creating animal drawer instances."""

    @staticmethod
    def create(animal_name: str, width: int = 200, height: int = 200) -> AnimalDrawer:
        """
        Create an animal drawer instance.

        Args:
            animal_name: Animal identifier (e.g., 'cat', 'dog')
            width: Canvas width in pixels
            height: Canvas height in pixels

        Returns:
            AnimalDrawer instance

        Raises:
            ValueError: If animal not registered
        """
        animal_class = AnimalRegistry.get(animal_name)
        
        if animal_class is None:
            available = ', '.join(AnimalRegistry.list_animals().keys())
            raise ValueError(
                f"Animal '{animal_name}' not registered. "
                f"Available: {available}"
            )
        
        return animal_class(width=width, height=height)

    @staticmethod
    def create_batch(specs: Dict[str, Dict[str, Any]]) -> Dict[str, AnimalDrawer]:
        """
        Create multiple animal drawers from specifications.

        Args:
            specs: Dictionary of {name: {'type': 'cat', 'width': 200, ...}}

        Returns:
            Dictionary of {name: AnimalDrawer instance}

        Raises:
            ValueError: If animal type not registered or invalid spec
        """
        result = {}
        for instance_name, spec in specs.items():
            if not isinstance(spec, dict):
                raise ValueError(f"Spec for '{instance_name}' must be dict")
            
            animal_type = spec.get('type')
            if not animal_type:
                raise ValueError(f"Spec for '{instance_name}' missing 'type'")
            
            width = spec.get('width', 200)
            height = spec.get('height', 200)
            
            result[instance_name] = AnimalFactory.create(animal_type, width, height)
        
        return result

    @staticmethod
    def get_available_animals() -> Dict[str, type]:
        """
        Get all available animal types.

        Returns:
            Dictionary of registered animals
        """
        return AnimalRegistry.list_animals()

    @staticmethod
    def is_available(animal_name: str) -> bool:
        """
        Check if animal type is available.

        Args:
            animal_name: Animal identifier

        Returns:
            True if available
        """
        return AnimalRegistry.is_registered(animal_name)
