"""Tests for FileOperationsUtil utility module."""

import pytest
import json
import os
import tempfile
from pathlib import Path
from src.components.file_operations_utils import FileOperationsUtil


class TestFileOperationsUtil:
    """Tests for file operations utility functions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_safe_write_and_read_json(self, temp_dir):
        """Test writing and reading JSON files."""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"name": "Test", "value": 42}
        
        # Write
        assert FileOperationsUtil.safe_write_json(file_path, data, create_backup=False) is True
        assert os.path.exists(file_path)
        
        # Read
        read_data = FileOperationsUtil.safe_read_json(file_path)
        assert read_data == data
    
    def test_safe_read_nonexistent_json(self, temp_dir):
        """Test reading non-existent JSON file."""
        file_path = os.path.join(temp_dir, "nonexistent.json")
        result = FileOperationsUtil.safe_read_json(file_path)
        assert result is None
    
    def test_safe_write_json_creates_directory(self, temp_dir):
        """Test that write_json creates directory if needed."""
        file_path = os.path.join(temp_dir, "subdir", "nested", "test.json")
        data = {"test": True}
        
        assert FileOperationsUtil.safe_write_json(file_path, data, create_backup=False) is True
        assert os.path.exists(file_path)
    
    def test_safe_write_json_creates_backup(self, temp_dir):
        """Test that backup is created when overwriting."""
        file_path = os.path.join(temp_dir, "test.json")
        
        # Write initial file
        data1 = {"version": 1}
        FileOperationsUtil.safe_write_json(file_path, data1, create_backup=False)
        
        # Overwrite with backup
        data2 = {"version": 2}
        FileOperationsUtil.safe_write_json(file_path, data2, create_backup=True)
        
        # Check backup exists
        backups = [f for f in os.listdir(temp_dir) if f.endswith('.bak')]
        assert len(backups) > 0
    
    def test_safe_write_and_read_text(self, temp_dir):
        """Test writing and reading text files."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Hello, World!\nLine 2\nLine 3"
        
        # Write
        assert FileOperationsUtil.safe_write_text(file_path, content, create_backup=False) is True
        
        # Read
        read_content = FileOperationsUtil.safe_read_text(file_path)
        assert read_content == content
    
    def test_safe_read_nonexistent_text(self, temp_dir):
        """Test reading non-existent text file."""
        file_path = os.path.join(temp_dir, "nonexistent.txt")
        result = FileOperationsUtil.safe_read_text(file_path)
        assert result is None
    
    def test_safe_append_text(self, temp_dir):
        """Test appending text to file."""
        file_path = os.path.join(temp_dir, "test.txt")
        
        # Write initial
        FileOperationsUtil.safe_write_text(file_path, "Line 1\n", create_backup=False)
        
        # Append
        assert FileOperationsUtil.safe_append_text(file_path, "Line 2\n") is True
        
        # Verify
        content = FileOperationsUtil.safe_read_text(file_path)
        assert "Line 1\nLine 2\n" == content
    
    def test_safe_append_creates_file(self, temp_dir):
        """Test that append creates file if it doesn't exist."""
        file_path = os.path.join(temp_dir, "new.txt")
        assert FileOperationsUtil.safe_append_text(file_path, "Content") is True
        assert os.path.exists(file_path)
    
    def test_file_exists(self, temp_dir):
        """Test file existence check."""
        file_path = os.path.join(temp_dir, "test.txt")
        
        assert FileOperationsUtil.file_exists(file_path) is False
        
        FileOperationsUtil.safe_write_text(file_path, "test", create_backup=False)
        assert FileOperationsUtil.file_exists(file_path) is True
    
    def test_get_file_size(self, temp_dir):
        """Test getting file size."""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Hello, World!"
        
        FileOperationsUtil.safe_write_text(file_path, content, create_backup=False)
        size = FileOperationsUtil.get_file_size(file_path)
        
        assert size == len(content.encode('utf-8'))
    
    def test_get_file_size_nonexistent(self, temp_dir):
        """Test getting size of non-existent file."""
        file_path = os.path.join(temp_dir, "nonexistent.txt")
        size = FileOperationsUtil.get_file_size(file_path)
        assert size is None
    
    def test_ensure_directory(self, temp_dir):
        """Test directory creation."""
        dir_path = os.path.join(temp_dir, "subdir", "nested")
        
        assert FileOperationsUtil.ensure_directory(dir_path) is True
        assert os.path.isdir(dir_path)
    
    def test_ensure_directory_existing(self, temp_dir):
        """Test ensure_directory with existing directory."""
        # Should not fail if directory already exists
        assert FileOperationsUtil.ensure_directory(temp_dir) is True
    
    def test_list_files(self, temp_dir):
        """Test listing files in directory."""
        # Create test files
        FileOperationsUtil.safe_write_text(os.path.join(temp_dir, "file1.txt"), "test1", create_backup=False)
        FileOperationsUtil.safe_write_text(os.path.join(temp_dir, "file2.txt"), "test2", create_backup=False)
        FileOperationsUtil.safe_write_json(os.path.join(temp_dir, "file3.json"), {"test": True}, create_backup=False)
        
        files = FileOperationsUtil.list_files(temp_dir)
        assert len(files) == 3
    
    def test_list_files_with_extension_filter(self, temp_dir):
        """Test listing files with extension filter."""
        FileOperationsUtil.safe_write_text(os.path.join(temp_dir, "file1.txt"), "test1", create_backup=False)
        FileOperationsUtil.safe_write_text(os.path.join(temp_dir, "file2.txt"), "test2", create_backup=False)
        FileOperationsUtil.safe_write_json(os.path.join(temp_dir, "file3.json"), {"test": True}, create_backup=False)
        
        txt_files = FileOperationsUtil.list_files(temp_dir, extension=".txt")
        assert len(txt_files) == 2
        assert all(f.endswith(".txt") for f in txt_files)
    
    def test_list_files_empty_directory(self, temp_dir):
        """Test listing files in empty directory."""
        files = FileOperationsUtil.list_files(temp_dir)
        assert len(files) == 0
    
    def test_list_files_nonexistent_directory(self, temp_dir):
        """Test listing files in non-existent directory."""
        nonexistent = os.path.join(temp_dir, "nonexistent")
        files = FileOperationsUtil.list_files(nonexistent)
        assert files == []
    
    def test_safe_write_json_with_invalid_path_permission(self):
        """Test write with permission error handling."""
        # Try to write to system directory (will fail)
        result = FileOperationsUtil.safe_write_json("/root/test.json", {"test": True}, create_backup=False)
        assert result is False
    
    def test_safe_read_invalid_json_format(self, temp_dir):
        """Test reading file with invalid JSON."""
        file_path = os.path.join(temp_dir, "invalid.json")
        FileOperationsUtil.safe_write_text(file_path, "{ invalid json }", create_backup=False)
        
        result = FileOperationsUtil.safe_read_json(file_path)
        assert result is None
