"""Tests for the job tracker service."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import redis

from app.services.job_tracker import JobTracker


class TestJobTracker:
    """Test cases for JobTracker class."""

    @pytest.fixture
    def job_tracker(self):
        """Create a job tracker with mocked Redis."""
        with patch("redis.from_url") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            tracker = JobTracker()
            tracker.redis_client = mock_client
            
            yield tracker

    def test_create_job(self, job_tracker):
        """Test creating a job."""
        file_id = "test-file"
        options = {"image_type": "color", "quality_mode": "standard"}
        
        job_id = job_tracker.create_job(file_id, options)
        
        assert job_id is not None
        assert len(job_id) == 36  # UUID length
        
        # Check Redis was called
        job_tracker.redis_client.hset.assert_called_once()
        call_args = job_tracker.redis_client.hset.call_args
        assert call_args[0][0].startswith("job:")

    def test_create_job_with_user(self, job_tracker):
        """Test creating a job with user ID."""
        file_id = "test-file"
        options = {}
        user_id = "test-user"
        
        job_id = job_tracker.create_job(file_id, options, user_id)
        
        # Check user jobs list was updated
        job_tracker.redis_client.lpush.assert_called_once()

    def test_get_job(self, job_tracker):
        """Test getting job data."""
        job_id = "test-job"
        
        # Mock Redis response
        job_tracker.redis_client.hgetall.return_value = {
            "job_id": job_id,
            "status": "completed",
            "progress": "1.0",
            "options": json.dumps({"test": "data"}),
        }
        
        result = job_tracker.get_job(job_id)
        
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == "completed"
        assert result["progress"] == 1.0
        assert result["options"] == {"test": "data"}

    def test_get_job_not_found(self, job_tracker):
        """Test getting non-existent job."""
        job_tracker.redis_client.hgetall.return_value = {}
        
        result = job_tracker.get_job("nonexistent")
        
        assert result is None

    def test_update_job(self, job_tracker):
        """Test updating job status."""
        job_id = "test-job"
        
        job_tracker.redis_client.exists.return_value = 1
        
        result = job_tracker.update_job(
            job_id,
            status="processing",
            progress=0.5,
        )
        
        assert result is True
        job_tracker.redis_client.hset.assert_called_once()

    def test_update_job_not_found(self, job_tracker):
        """Test updating non-existent job."""
        job_tracker.redis_client.exists.return_value = 0
        
        result = job_tracker.update_job("nonexistent", status="processing")
        
        assert result is False

    def test_update_progress(self, job_tracker):
        """Test updating job progress."""
        job_id = "test-job"
        
        job_tracker.redis_client.exists.return_value = 1
        
        result = job_tracker.update_progress(job_id, 0.7, "Processing...")
        
        assert result is True
        job_tracker.redis_client.hset.assert_called_once()

    def test_delete_job(self, job_tracker):
        """Test deleting a job."""
        job_id = "test-job"
        
        # Mock job data
        job_tracker.redis_client.hgetall.return_value = {
            "job_id": job_id,
            "user_id": "test-user",
        }
        job_tracker.redis_client.delete.return_value = 1
        
        result = job_tracker.delete_job(job_id)
        
        assert result is True
        job_tracker.redis_client.delete.assert_called_once()
        job_tracker.redis_client.lrem.assert_called_once()

    def test_delete_job_not_found(self, job_tracker):
        """Test deleting non-existent job."""
        job_tracker.redis_client.hgetall.return_value = {}
        job_tracker.redis_client.delete.return_value = 0

        result = job_tracker.delete_job("nonexistent")

        assert result is False

    def test_get_user_jobs(self, job_tracker):
        """Test getting jobs for a user."""
        user_id = "test-user"
        
        job_tracker.redis_client.lrange.return_value = ["job-1", "job-2"]
        job_tracker.redis_client.hgetall.side_effect = [
            {"job_id": "job-1", "status": "completed"},
            {"job_id": "job-2", "status": "pending"},
        ]
        
        result = job_tracker.get_user_jobs(user_id)
        
        assert len(result) == 2
        assert result[0]["job_id"] == "job-1"

    def test_get_jobs_by_status(self, job_tracker):
        """Test getting jobs by status."""
        # Mock scan to return job keys
        job_tracker.redis_client.scan.side_effect = [
            (0, ["job:job-1", "job:job-2"]),  # First call
        ]
        
        job_tracker.redis_client.hgetall.side_effect = [
            {"job_id": "job-1", "status": "pending", "options": "{}"},
            {"job_id": "job-2", "status": "completed", "options": "{}"},
        ]
        
        result = job_tracker.get_jobs_by_status("pending")
        
        assert len(result) == 1
        assert result[0]["job_id"] == "job-1"

    def test_get_pending_jobs(self, job_tracker):
        """Test getting pending jobs."""
        with patch.object(job_tracker, "get_jobs_by_status") as mock_get:
            mock_get.return_value = [{"job_id": "job-1"}]
            
            result = job_tracker.get_pending_jobs()
            
            mock_get.assert_called_once_with("pending", 100)
            assert len(result) == 1

    def test_get_processing_jobs(self, job_tracker):
        """Test getting processing jobs."""
        with patch.object(job_tracker, "get_jobs_by_status") as mock_get:
            mock_get.return_value = [{"job_id": "job-1"}]
            
            result = job_tracker.get_processing_jobs()
            
            mock_get.assert_called_once_with("processing", 100)

    def test_cleanup_old_jobs(self, job_tracker):
        """Test cleaning up old jobs."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        
        job_tracker.redis_client.scan.side_effect = [
            (0, ["job:old-job"]),
        ]
        job_tracker.redis_client.hget.return_value = old_time
        job_tracker.redis_client.delete.return_value = 1
        
        result = job_tracker.cleanup_old_jobs(days=30)
        
        assert result == 1
        job_tracker.redis_client.delete.assert_called_once()

    def test_get_queue_stats(self, job_tracker):
        """Test getting queue stats."""
        with patch.object(job_tracker, "get_jobs_by_status") as mock_get:
            mock_get.side_effect = [
                [{}, {}],  # pending: 2
                [{}],      # processing: 1
                [{}, {}, {}],  # completed: 3
                [],        # failed: 0
            ]
            
            result = job_tracker.get_queue_stats()
            
            assert result["pending"] == 2
            assert result["processing"] == 1
            assert result["completed"] == 3
            assert result["failed"] == 0

    def test_get_health_status_healthy(self, job_tracker):
        """Test health check when Redis is healthy."""
        job_tracker.redis_client.ping.return_value = True
        job_tracker.redis_client.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": 5,
        }
        
        result = job_tracker.get_health_status()
        
        assert result["status"] == "healthy"
        assert result["connected"] is True

    def test_get_health_status_unhealthy(self, job_tracker):
        """Test health check when Redis is down."""
        job_tracker.redis_client.ping.side_effect = redis.ConnectionError("Connection refused")
        
        result = job_tracker.get_health_status()
        
        assert result["status"] == "unhealthy"
        assert result["connected"] is False
