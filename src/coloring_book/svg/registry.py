"""Animal registry for managing available animal types."""

from typing import Dict, Type, Optional
from .base import AnimalDrawer
from .animals import CatDrawer, DogDrawer, BirdDrawer


class AnimalRegistry:
    """Registry for managing animal drawer classes."""

    _animals: Dict[str, Type[AnimalDrawer]] = {}

    @classmethod
    def register(cls, name: str, animal_class: Type[AnimalDrawer]) -> None:
        """
        Register an animal class.

        Args:
            name: Animal identifier (e.g., 'cat', 'dog')
            animal_class: AnimalDrawer subclass

        Raises:
            ValueError: If name already registered or invalid class
        """
        if not issubclass(animal_class, AnimalDrawer):
            raise ValueError(f"Animal class must inherit from AnimalDrawer")
        
        if name in cls._animals:
            raise ValueError(f"Animal '{name}' already registered")
        
        cls._animals[name] = animal_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[AnimalDrawer]]:
        """
        Get a registered animal class.

        Args:
            name: Animal identifier

        Returns:
            Animal class or None if not registered
        """
        return cls._animals.get(name)

    @classmethod
    def list_animals(cls) -> Dict[str, Type[AnimalDrawer]]:
        """
        Get all registered animals.

        Returns:
            Dictionary of name -> class mappings
        """
        return cls._animals.copy()

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if animal is registered.

        Args:
            name: Animal identifier

        Returns:
            True if registered
        """
        return name in cls._animals

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister an animal.

        Args:
            name: Animal identifier

        Returns:
            True if unregistered, False if not found
        """
        if name in cls._animals:
            del cls._animals[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered animals."""
        cls._animals.clear()

    @classmethod
    def count(cls) -> int:
        """Get number of registered animals."""
        return len(cls._animals)


# Initialize default animals
AnimalRegistry.register("cat", CatDrawer)
AnimalRegistry.register("dog", DogDrawer)
AnimalRegistry.register("bird", BirdDrawer)
