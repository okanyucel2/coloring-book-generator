"""
ZIP Export Service
Handles file aggregation, streaming, and ZIP generation for batch downloads.
"""

import os
import zipfile
import io
from pathlib import Path
from typing import List, Optional, Dict, BinaryIO
from datetime import datetime


class ZipExportService:
    """
    Service for creating and managing ZIP exports of batch results
    Supports streaming and size-limited exports.
    """

    MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB limit
    CHUNK_SIZE = 8192

    def __init__(self, temp_dir: str):
        """
        Initialize ZIP export service

        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

    def create_zip(
        self,
        output_path: str,
        files: List[Dict[str, str]],
        compression: str = "deflate"
    ) -> Dict:
        """
        Create ZIP file from list of files

        Args:
            output_path: Output ZIP file path
            files: List of dicts with 'path' and 'arcname' keys
            compression: ZIP compression method

        Returns:
            Dict with zip_path, size_bytes, file_count, status

        Raises:
            Exception: If total size exceeds limit or file not found
        """
        try:
            total_size = 0
            file_count = 0

            # Pre-check total size
            for file_dict in files:
                file_path = file_dict.get("path")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                file_size = os.path.getsize(file_path)
                total_size += file_size

                if total_size > self.MAX_ZIP_SIZE:
                    raise Exception(
                        f"Total file size ({total_size} bytes) exceeds limit ({self.MAX_ZIP_SIZE} bytes)"
                    )

            # Create ZIP
            compression_type = (
                zipfile.ZIP_DEFLATED if compression == "deflate" else zipfile.ZIP_STORED
            )

            with zipfile.ZipFile(output_path, "w", compression_type) as zf:
                for file_dict in files:
                    file_path = file_dict.get("path")
                    arcname = file_dict.get("arcname", os.path.basename(file_path))

                    try:
                        zf.write(file_path, arcname=arcname)
                        file_count += 1
                    except Exception as e:
                        # Continue with next file if one fails
                        print(f"Warning: Failed to add {file_path} to ZIP: {e}")
                        continue

            # Verify ZIP was created
            if not os.path.exists(output_path):
                raise Exception("ZIP file creation failed")

            zip_size = os.path.getsize(output_path)

            return {
                "status": "success",
                "zip_path": output_path,
                "size_bytes": zip_size,
                "file_count": file_count,
                "created_at": datetime.utcnow().isoformat(),
            }

        except FileNotFoundError as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "file_not_found",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "unknown",
            }

    def stream_zip(
        self,
        files: List[Dict[str, str]],
        compression: str = "deflate"
    ) -> BinaryIO:
        """
        Create ZIP file in memory and return stream for download

        Args:
            files: List of dicts with 'path' and 'arcname' keys
            compression: ZIP compression method

        Returns:
            BytesIO object ready for streaming

        Raises:
            Exception: If files not found or size limit exceeded
        """
        zip_buffer = io.BytesIO()
        compression_type = (
            zipfile.ZIP_DEFLATED if compression == "deflate" else zipfile.ZIP_STORED
        )

        try:
            total_size = 0

            # Pre-check files exist
            for file_dict in files:
                file_path = file_dict.get("path")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                file_size = os.path.getsize(file_path)
                total_size += file_size

                if total_size > self.MAX_ZIP_SIZE:
                    raise Exception("Total file size exceeds 500MB limit")

            # Create ZIP in memory
            with zipfile.ZipFile(zip_buffer, "w", compression_type) as zf:
                for file_dict in files:
                    file_path = file_dict.get("path")
                    arcname = file_dict.get("arcname", os.path.basename(file_path))

                    try:
                        zf.write(file_path, arcname=arcname)
                    except Exception as e:
                        print(f"Warning: Failed to add {file_path}: {e}")
                        continue

            zip_buffer.seek(0)
            return zip_buffer

        except Exception as e:
            zip_buffer.close()
            raise e

    def add_text_to_zip(
        self,
        zip_path: str,
        filename: str,
        content: str
    ) -> bool:
        """
        Add text file to existing ZIP

        Args:
            zip_path: Path to ZIP file
            filename: Filename in ZIP
            content: Text content

        Returns:
            True if successful
        """
        try:
            with zipfile.ZipFile(zip_path, "a") as zf:
                zf.writestr(filename, content)
            return True
        except Exception as e:
            print(f"Error adding text to ZIP: {e}")
            return False

    def extract_zip(self, zip_path: str, extract_to: str) -> Dict:
        """
        Extract ZIP file to directory

        Args:
            zip_path: Path to ZIP file
            extract_to: Destination directory

        Returns:
            Dict with status and extracted file count
        """
        try:
            Path(extract_to).mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_to)
                file_count = len(zf.namelist())

            return {
                "status": "success",
                "extract_path": extract_to,
                "file_count": file_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def list_zip_contents(self, zip_path: str) -> List[Dict]:
        """
        List files in ZIP

        Args:
            zip_path: Path to ZIP file

        Returns:
            List of file dicts with name, size, compressed_size
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                contents = []
                for info in zf.infolist():
                    contents.append({
                        "name": info.filename,
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                        "is_dir": info.is_dir(),
                    })
                return contents
        except Exception as e:
            print(f"Error listing ZIP contents: {e}")
            return []

    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Delete temporary file

        Args:
            file_path: Path to file to delete

        Returns:
            True if successful
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False

    def validate_zip(self, zip_path: str) -> Dict:
        """
        Validate ZIP file integrity

        Args:
            zip_path: Path to ZIP file

        Returns:
            Dict with validation results
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad_file = zf.testzip()

                if bad_file:
                    return {
                        "valid": False,
                        "error": f"Bad file in ZIP: {bad_file}",
                    }

                return {
                    "valid": True,
                    "file_count": len(zf.namelist()),
                    "total_size": sum(info.file_size for info in zf.infolist()),
                }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }
