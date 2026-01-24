"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest


@pytest.fixture
def project_dir():
    """Return project root directory"""
    return project_root


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide temporary output directory for tests"""
    return tmp_path / "output"
