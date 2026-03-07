"""Tests for the API."""

import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


client = TestClient(app)


class TestAPI:
    """Test cases for API endpoints."""

    def test_root(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()
        assert "version" in response.json()

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_api_info(self):
        """Test API info endpoint."""
        response = client.get("/api/v1")
        assert response.status_code == 200
        assert "endpoints" in response.json()

    def test_upload_no_file(self):
        """Test upload without file."""
        response = client.post("/api/v1/upload")
        assert response.status_code == 422  # Validation error

    def test_upload_invalid_format(self):
        """Test upload with invalid file format."""
        files = {"file": ("test.txt", io.BytesIO(b"invalid"), "text/plain")}
        response = client.post("/api/v1/upload", files=files)
        assert response.status_code == 400

    def test_upload_valid_image(self):
        """Test upload with valid image."""
        # Create test image
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        files = {"file": ("test.png", img_bytes, "image/png")}
        
        with patch("app.api.routes.file_manager.save_upload") as mock_save:
            mock_save.return_value = {
                "file_id": "test-id",
                "filename": "test.png",
                "size": 1234,
                "content_type": "image/png",
            }
            
            response = client.post("/api/v1/upload", files=files)
            assert response.status_code == 200
            assert response.json()["file_id"] == "test-id"

    def test_convert_no_file_id(self):
        """Test convert without file_id."""
        response = client.post("/api/v1/convert", data={})
        assert response.status_code == 422

    def test_convert_file_not_found(self):
        """Test convert with non-existent file."""
        with patch("app.api.routes.file_manager.get_upload") as mock_get:
            mock_get.return_value = None
            
            response = client.post(
                "/api/v1/convert",
                data={"file_id": "nonexistent"}
            )
            assert response.status_code == 404

    def test_convert_success(self):
        """Test successful conversion request."""
        with patch("app.api.routes.file_manager.get_upload") as mock_get, \
             patch("app.api.routes.job_tracker.create_job") as mock_create, \
             patch("app.api.routes.convert_image_task") as mock_task:
            
            mock_get.return_value = Path("/tmp/test.png")
            mock_create.return_value = "test-job-id"
            mock_task.delay.return_value = Mock()
            
            response = client.post(
                "/api/v1/convert",
                data={
                    "file_id": "test-file-id",
                    "image_type": "color",
                    "quality_mode": "standard",
                }
            )
            assert response.status_code == 200
            assert response.json()["job_id"] == "test-job-id"
            assert response.json()["status"] == "pending"

    def test_convert_invalid_image_type(self):
        """Test convert with invalid image_type."""
        with patch("app.api.routes.file_manager.get_upload") as mock_get:
            mock_get.return_value = Path("/tmp/test.png")
            
            response = client.post(
                "/api/v1/convert",
                data={
                    "file_id": "test-file-id",
                    "image_type": "invalid",
                }
            )
            assert response.status_code == 400

    def test_convert_invalid_quality(self):
        """Test convert with invalid quality_mode."""
        with patch("app.api.routes.file_manager.get_upload") as mock_get:
            mock_get.return_value = Path("/tmp/test.png")
            
            response = client.post(
                "/api/v1/convert",
                data={
                    "file_id": "test-file-id",
                    "quality_mode": "invalid",
                }
            )
            assert response.status_code == 400

    def test_get_status_job_not_found(self):
        """Test status endpoint with non-existent job."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/v1/status/nonexistent")
            assert response.status_code == 404

    def test_get_status_success(self):
        """Test status endpoint with existing job."""
        from datetime import datetime
        
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = {
                "job_id": "test-job",
                "status": "completed",
                "progress": 1.0,
                "error": None,
                "result_url": "/api/v1/result/test-job",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "processing_time": 5.0,
            }
            
            response = client.get("/api/v1/status/test-job")
            assert response.status_code == 200
            assert response.json()["status"] == "completed"

    def test_download_result_job_not_found(self):
        """Test download with non-existent job."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/v1/result/nonexistent")
            assert response.status_code == 404

    def test_download_result_not_completed(self):
        """Test download with incomplete job."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = {
                "job_id": "test-job",
                "status": "processing",
                "progress": 0.5,
            }
            
            response = client.get("/api/v1/result/test-job")
            assert response.status_code == 400

    def test_download_result_failed(self):
        """Test download with failed job."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = {
                "job_id": "test-job",
                "status": "failed",
                "error": "Conversion failed",
            }
            
            response = client.get("/api/v1/result/test-job")
            assert response.status_code == 400

    def test_list_jobs(self):
        """Test list jobs endpoint."""
        with patch("app.api.routes.job_tracker.get_jobs_by_status") as mock_get:
            mock_get.return_value = []
            
            response = client.get("/api/v1/jobs")
            assert response.status_code == 200
            assert "jobs" in response.json()

    def test_list_jobs_with_status(self):
        """Test list jobs with status filter."""
        with patch("app.api.routes.job_tracker.get_jobs_by_status") as mock_get:
            mock_get.return_value = []
            
            response = client.get("/api/v1/jobs?status=pending")
            assert response.status_code == 200

    def test_delete_job_not_found(self):
        """Test delete job with non-existent job."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get:
            mock_get.return_value = None
            
            response = client.delete("/api/v1/jobs/nonexistent")
            assert response.status_code == 404

    def test_delete_job_success(self):
        """Test successful job deletion."""
        with patch("app.api.routes.job_tracker.get_job") as mock_get, \
             patch("app.api.routes.file_manager.delete_result") as mock_delete_result, \
             patch("app.api.routes.job_tracker.delete_job") as mock_delete_job:
            
            mock_get.return_value = {"job_id": "test-job"}
            mock_delete_result.return_value = True
            mock_delete_job.return_value = True
            
            response = client.delete("/api/v1/jobs/test-job")
            assert response.status_code == 200
            assert response.json()["status"] == "deleted"

    def test_storage_stats(self):
        """Test storage stats endpoint."""
        with patch("app.api.routes.file_manager.get_storage_stats") as mock_stats:
            mock_stats.return_value = {
                "uploads": {"count": 10, "size_mb": 100},
                "results": {"count": 5, "size_mb": 50},
            }
            
            response = client.get("/api/v1/storage/stats")
            assert response.status_code == 200
            assert "uploads" in response.json()

    def test_queue_stats(self):
        """Test queue stats endpoint."""
        with patch("app.api.routes.job_tracker.get_queue_stats") as mock_stats:
            mock_stats.return_value = {
                "pending": 5,
                "processing": 2,
                "completed": 100,
                "failed": 3,
            }
            
            response = client.get("/api/v1/queue/stats")
            assert response.status_code == 200

    def test_cleanup_storage(self):
        """Test storage cleanup endpoint."""
        with patch("app.workers.tasks.cleanup_old_files_task") as mock_task:
            mock_task.delay.return_value = Mock()

            response = client.post("/api/v1/storage/cleanup?days=30")
            assert response.status_code == 200
            assert response.json()["status"] == "cleanup_started"


class TestAPIIntegration:
    """Integration tests for API."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image."""
        img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        return img_bytes

    def test_full_workflow(self, sample_image):
        """Test full upload-convert-status workflow."""
        # This is a simplified test - in reality would need running services
        files = {"file": ("test.png", sample_image, "image/png")}
        
        # Upload would need actual file manager
        # Convert would need actual job tracker and celery
        # Status would need actual job data
        pass
