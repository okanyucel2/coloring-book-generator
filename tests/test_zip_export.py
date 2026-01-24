"""
Unit tests for ZIP Export Service
Tests file aggregation, streaming, and ZIP integrity.
Target: 90%+ code coverage
"""

import pytest
import os
import tempfile
import zipfile

from coloring_book.services.zip_export import ZipExportService


class TestZipExportService:
    """Tests for ZIP export functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def service(self, temp_dir):
        """Create ZIP export service"""
        return ZipExportService(temp_dir)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample test files"""
        files = []

        for i in range(3):
            file_path = os.path.join(temp_dir, f"test_{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"Test content {i}\n" * 100)

            files.append({
                "path": file_path,
                "arcname": f"file_{i}.txt"
            })

        return files

    def test_service_initialization(self, service, temp_dir):
        """Should initialize with temp directory"""
        assert service.temp_dir == temp_dir
        assert os.path.exists(temp_dir)

    def test_create_simple_zip(self, service, temp_dir, sample_files):
        """Should create ZIP from list of files"""
        output_path = os.path.join(temp_dir, "output.zip")

        result = service.create_zip(output_path, sample_files)

        assert result["status"] == "success"
        assert os.path.exists(output_path)
        assert result["file_count"] == 3
        assert result["size_bytes"] > 0

    def test_create_zip_missing_file(self, service, temp_dir):
        """Should fail gracefully for missing files"""
        output_path = os.path.join(temp_dir, "output.zip")

        files = [{
            "path": "/nonexistent/file.txt",
            "arcname": "file.txt"
        }]

        result = service.create_zip(output_path, files)

        assert result["status"] == "error"
        assert "error_type" in result

    def test_stream_zip_to_buffer(self, service, sample_files):
        """Should create ZIP in memory stream"""
        stream = service.stream_zip(sample_files)

        assert stream is not None
        stream.seek(0)
        
        with zipfile.ZipFile(stream, "r") as zf:
            names = zf.namelist()
            assert len(names) == 3

    def test_add_text_to_zip(self, service, temp_dir, sample_files):
        """Should add text content to existing ZIP"""
        output_path = os.path.join(temp_dir, "output.zip")
        service.create_zip(output_path, sample_files)

        success = service.add_text_to_zip(
            output_path,
            "README.txt",
            "This is a readme file"
        )

        assert success is True

        with zipfile.ZipFile(output_path, "r") as zf:
            assert "README.txt" in zf.namelist()

    def test_extract_zip(self, service, temp_dir, sample_files):
        """Should extract ZIP to directory"""
        zip_path = os.path.join(temp_dir, "test.zip")
        extract_dir = os.path.join(temp_dir, "extracted")

        service.create_zip(zip_path, sample_files)

        result = service.extract_zip(zip_path, extract_dir)

        assert result["status"] == "success"
        assert os.path.exists(extract_dir)
        assert result["file_count"] == 3

    def test_list_zip_contents(self, service, temp_dir, sample_files):
        """Should list files in ZIP with metadata"""
        zip_path = os.path.join(temp_dir, "test.zip")
        service.create_zip(zip_path, sample_files)

        contents = service.list_zip_contents(zip_path)

        assert len(contents) == 3
        assert all("name" in item for item in contents)
        assert all("size" in item for item in contents)

    def test_cleanup_temp_file_exists(self, service, temp_dir):
        """Should delete existing file"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        assert os.path.exists(test_file)

        success = service.cleanup_temp_file(test_file)

        assert success is True
        assert not os.path.exists(test_file)

    def test_validate_zip_valid(self, service, temp_dir, sample_files):
        """Should validate correct ZIP file"""
        zip_path = os.path.join(temp_dir, "test.zip")
        service.create_zip(zip_path, sample_files)

        result = service.validate_zip(zip_path)

        assert result["valid"] is True
        assert result["file_count"] == 3
        assert result["total_size"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
