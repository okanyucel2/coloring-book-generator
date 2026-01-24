"""
Utility module for reusable file operations.
Consolidates common file I/O patterns to reduce code duplication
and improve maintainability across the project.
"""

import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path


class FileOperationsUtil:
    """Utility class for common file operations with error handling."""
    
    @staticmethod
    def safe_read_json(file_path: str) -> Optional[Dict]:
        """Safely read JSON file with error handling.
        
        Args:
            file_path: Path to JSON file.
        
        Returns:
            Parsed JSON dict or None if file doesn't exist/invalid JSON.
        """
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading JSON from {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def safe_write_json(file_path: str, data: Dict, create_backup: bool = True) -> bool:
        """Safely write JSON file with backup capability.
        
        Args:
            file_path: Path to JSON file.
            data: Dictionary to write as JSON.
            create_backup: If True, create timestamped backup before overwriting.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create backup if file exists and backup requested
            if create_backup and os.path.exists(file_path):
                from datetime import datetime
                backup_path = f"{file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                with open(file_path, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            # Write JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error writing JSON to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def safe_read_text(file_path: str) -> Optional[str]:
        """Safely read text file with error handling.
        
        Args:
            file_path: Path to text file.
        
        Returns:
            File contents as string or None if error.
        """
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError as e:
            print(f"Error reading text from {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def safe_write_text(file_path: str, content: str, create_backup: bool = True) -> bool:
        """Safely write text file with backup capability.
        
        Args:
            file_path: Path to text file.
            content: Text content to write.
            create_backup: If True, create timestamped backup before overwriting.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create backup if file exists and backup requested
            if create_backup and os.path.exists(file_path):
                from datetime import datetime
                backup_path = f"{file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                with open(file_path, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            # Write text file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except IOError as e:
            print(f"Error writing text to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def safe_append_text(file_path: str, content: str) -> bool:
        """Safely append text to file.
        
        Args:
            file_path: Path to text file.
            content: Text content to append.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except IOError as e:
            print(f"Error appending text to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """Check if file exists.
        
        Args:
            file_path: Path to file.
        
        Returns:
            True if file exists, False otherwise.
        """
        return os.path.exists(file_path)
    
    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """Get file size in bytes.
        
        Args:
            file_path: Path to file.
        
        Returns:
            File size in bytes or None if file doesn't exist.
        """
        try:
            if os.path.exists(file_path):
                return os.path.getsize(file_path)
            return None
        except OSError:
            return None
    
    @staticmethod
    def ensure_directory(dir_path: str) -> bool:
        """Ensure directory exists, creating if needed.
        
        Args:
            dir_path: Path to directory.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except OSError:
            return False
    
    @staticmethod
    def list_files(dir_path: str, extension: Optional[str] = None) -> List[str]:
        """List files in directory with optional extension filter.
        
        Args:
            dir_path: Path to directory.
            extension: Optional file extension filter (e.g., '.json').
        
        Returns:
            List of file paths.
        """
        try:
            if not os.path.isdir(dir_path):
                return []
            
            files = []
            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)
                if os.path.isfile(filepath):
                    if extension is None or filename.endswith(extension):
                        files.append(filepath)
            return files
        except OSError:
            return []
