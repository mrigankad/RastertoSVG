"""Tests for the file manager service."""

import io
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.file_manager import FileManager


class TestFileManager:
    """Test cases for FileManager class."""

    @pytest.fixture
    def file_manager(self, tmp_path):
        """Create a file manager with temporary directories."""
        from app.config import Settings
        
        # Create temporary directories
        upload_dir = tmp_path / "uploads"
        result_dir = tmp_path / "results"
        
        # Mock settings
        settings = Settings(
            UPLOAD_DIR=upload_dir,
            RESULT_DIR=result_dir,
            MAX_IMAGE_SIZE=10 * 1024 * 1024,  # 10MB
        )
        
        # Create file manager with mocked settings
        fm = FileManager()
        fm.upload_dir = upload_dir
        fm.result_dir = result_dir
        fm.max_file_size = 10 * 1024 * 1024  # 10MB

        return fm

    @pytest.fixture
    def sample_upload_file(self):
        """Create a sample upload file."""
        content = b"fake image content"
        file = io.BytesIO(content)
        
        class MockUploadFile:
            def __init__(self):
                self.file = file
                self.filename = "test.png"
                self.content_type = "image/png"
                
            async def read(self):
                return content
        
        return MockUploadFile()

    @pytest.mark.asyncio
    async def test_save_upload(self, file_manager, sample_upload_file):
        """Test saving an upload."""
        result = await file_manager.save_upload(sample_upload_file)
        
        assert "file_id" in result
        assert result["filename"] == "test.png"
        assert result["extension"] == ".png"
        assert result["content_type"] == "image/png"
        
        # Check file exists
        assert Path(result["path"]).exists()

    @pytest.mark.asyncio
    async def test_save_upload_invalid_format(self, file_manager):
        """Test saving upload with invalid format."""
        content = b"fake content"
        
        class MockUploadFile:
            def __init__(self):
                self.file = io.BytesIO(content)
                self.filename = "test.txt"
                self.content_type = "text/plain"
                
            async def read(self):
                return content
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            await file_manager.save_upload(MockUploadFile())

    @pytest.mark.asyncio
    async def test_save_upload_empty_file(self, file_manager):
        """Test saving empty file."""
        content = b""
        
        class MockUploadFile:
            def __init__(self):
                self.file = io.BytesIO(content)
                self.filename = "test.png"
                self.content_type = "image/png"
                
            async def read(self):
                return content
        
        with pytest.raises(ValueError, match="File is empty"):
            await file_manager.save_upload(MockUploadFile())

    @pytest.mark.asyncio
    async def test_save_upload_too_large(self, file_manager):
        """Test saving file that exceeds size limit."""
        content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        class MockUploadFile:
            def __init__(self):
                self.file = io.BytesIO(content)
                self.filename = "test.png"
                self.content_type = "image/png"
                
            async def read(self):
                return content
        
        with pytest.raises(ValueError, match="File too large"):
            await file_manager.save_upload(MockUploadFile())

    def test_save_result(self, file_manager):
        """Test saving a result."""
        job_id = "test-job"
        svg_content = "<svg></svg>"
        metadata = {"test": "data"}
        
        result_path = file_manager.save_result(job_id, svg_content, metadata)
        
        assert Path(result_path).exists()
        
        # Check content
        with open(result_path, "r") as f:
            assert f.read() == svg_content
        
        # Check metadata
        import json
        meta_path = Path(result_path).parent / f"{job_id}.json"
        with open(meta_path, "r") as f:
            saved_meta = json.load(f)
            assert saved_meta["test"] == "data"

    @pytest.mark.asyncio
    async def test_get_upload(self, file_manager, sample_upload_file):
        """Test getting uploaded file."""
        result = await file_manager.save_upload(sample_upload_file)
        file_id = result["file_id"]
        
        found_path = file_manager.get_upload(file_id)
        assert found_path is not None
        assert found_path.exists()

    def test_get_upload_not_found(self, file_manager):
        """Test getting non-existent upload."""
        result = file_manager.get_upload("nonexistent")
        assert result is None

    def test_get_result(self, file_manager):
        """Test getting result."""
        job_id = "test-job"
        file_manager.save_result(job_id, "<svg></svg>")
        
        found_path = file_manager.get_result(job_id)
        assert found_path is not None
        assert found_path.exists()

    def test_get_result_not_found(self, file_manager):
        """Test getting non-existent result."""
        result = file_manager.get_result("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_upload(self, file_manager, sample_upload_file):
        """Test deleting upload."""
        result = await file_manager.save_upload(sample_upload_file)
        file_id = result["file_id"]
        
        assert file_manager.delete_upload(file_id) is True
        assert file_manager.get_upload(file_id) is None

    def test_delete_upload_not_found(self, file_manager):
        """Test deleting non-existent upload."""
        assert file_manager.delete_upload("nonexistent") is False

    def test_delete_result(self, file_manager):
        """Test deleting result."""
        job_id = "test-job"
        file_manager.save_result(job_id, "<svg></svg>")
        
        assert file_manager.delete_result(job_id) is True
        assert file_manager.get_result(job_id) is None

    def test_delete_result_not_found(self, file_manager):
        """Test deleting non-existent result."""
        assert file_manager.delete_result("nonexistent") is False

    def test_cleanup_old_files(self, file_manager):
        """Test cleanup of old files."""
        # Create old directory
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y%m%d")
        old_dir = file_manager.upload_dir / old_date
        old_dir.mkdir(parents=True, exist_ok=True)
        (old_dir / "test.txt").write_text("old file")

        # Make the directory old enough to be deleted
        old_time = (datetime.now() - timedelta(days=35)).timestamp()
        import os
        os.utime(old_dir, (old_time, old_time))

        # Cleanup
        result = file_manager.cleanup_old_files(days=30)

        assert result["deleted_upload_dirs"] >= 1
        assert not old_dir.exists()

    def test_storage_stats(self, file_manager):
        """Test getting storage stats."""
        # Create some test files in date-based directories
        today = datetime.now().strftime("%Y%m%d")
        upload_date_dir = file_manager.upload_dir / today
        result_date_dir = file_manager.result_dir / today
        upload_date_dir.mkdir(parents=True, exist_ok=True)
        result_date_dir.mkdir(parents=True, exist_ok=True)

        (upload_date_dir / "test1.txt").write_text("a" * 1000)
        (result_date_dir / "test2.txt").write_text("b" * 500)

        stats = file_manager.get_storage_stats()

        assert "uploads" in stats
        assert "results" in stats
        assert stats["uploads"]["count"] == 1
        assert stats["results"]["count"] == 1
        assert stats["uploads"]["size_bytes"] == 1000
        assert stats["results"]["size_bytes"] == 500

    def test_get_result_with_metadata(self, file_manager):
        """Test getting result with metadata."""
        job_id = "test-job"
        metadata = {"key": "value"}
        file_manager.save_result(job_id, "<svg></svg>", metadata)
        
        result_path, result_meta = file_manager.get_result_with_metadata(job_id)
        
        assert result_path is not None
        assert result_meta is not None
        assert result_meta["key"] == "value"

    def test_get_result_metadata_not_found(self, file_manager):
        """Test getting metadata when file doesn't exist."""
        metadata = file_manager.get_result_metadata("nonexistent")
        assert metadata is None
