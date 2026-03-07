"""Job tracking service using Redis."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class JobTracker:
    """Tracks conversion job status using Redis."""

    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.job_prefix = "job:"
        self.user_jobs_prefix = "user_jobs:"
        self.ttl = 30 * 24 * 60 * 60  # 30 days in seconds

    def create_job(
        self,
        file_id: str,
        options: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        Create a new job record.

        Args:
            file_id: ID of the uploaded file
            options: Conversion options
            user_id: Optional user ID for tracking

        Returns:
            Job ID
        """
        job_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        job_data = {
            "job_id": job_id,
            "file_id": file_id,
            "status": "pending",
            "progress": 0.0,
            "error": None,
            "result_url": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "processing_time": None,
            "options": json.dumps(options),
            "user_id": user_id,
        }

        # Store job data
        key = f"{self.job_prefix}{job_id}"
        self.redis_client.hset(key, mapping=job_data)
        self.redis_client.expire(key, self.ttl)

        # Add to user's job list if user_id provided
        if user_id:
            user_jobs_key = f"{self.user_jobs_prefix}{user_id}"
            self.redis_client.lpush(user_jobs_key, job_id)
            self.redis_client.expire(user_jobs_key, self.ttl)

        logger.info(f"Created job: {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        key = f"{self.job_prefix}{job_id}"
        data = self.redis_client.hgetall(key)

        if not data:
            return None

        # Parse JSON fields
        if "options" in data:
            try:
                data["options"] = json.loads(data["options"])
            except json.JSONDecodeError:
                data["options"] = {}

        # Convert numeric fields
        if "progress" in data:
            data["progress"] = float(data["progress"])
        if "processing_time" in data and data["processing_time"]:
            data["processing_time"] = float(data["processing_time"])

        return data

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        result_url: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> bool:
        """
        Update job status and metadata.

        Args:
            job_id: Job ID
            status: New status (pending, processing, completed, failed)
            progress: Progress value (0.0 to 1.0)
            error: Error message
            result_url: URL to download result
            processing_time: Processing time in seconds

        Returns:
            True if updated successfully
        """
        key = f"{self.job_prefix}{job_id}"

        if not self.redis_client.exists(key):
            return False

        updates = {"updated_at": datetime.now(timezone.utc).isoformat()}

        if status:
            updates["status"] = status
            if status in ["completed", "failed"]:
                updates["completed_at"] = datetime.now(timezone.utc).isoformat()

        if progress is not None:
            updates["progress"] = str(progress)

        if error is not None:
            updates["error"] = error

        if result_url is not None:
            updates["result_url"] = result_url

        if processing_time is not None:
            updates["processing_time"] = str(processing_time)

        self.redis_client.hset(key, mapping=updates)
        return True

    def update_progress(self, job_id: str, progress: float, message: Optional[str] = None):
        """Update job progress."""
        key = f"{self.job_prefix}{job_id}"

        if not self.redis_client.exists(key):
            return False

        updates = {
            "progress": str(progress),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if message:
            updates["status_message"] = message

        self.redis_client.hset(key, mapping=updates)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Delete a job record."""
        key = f"{self.job_prefix}{job_id}"

        # Get job data first to find user_id
        job_data = self.get_job(job_id)

        # Delete job
        result = self.redis_client.delete(key) > 0

        # Remove from user's job list
        if job_data and job_data.get("user_id"):
            user_jobs_key = f"{self.user_jobs_prefix}{job_data['user_id']}"
            self.redis_client.lrem(user_jobs_key, 0, job_id)

        if result:
            logger.info(f"Deleted job: {job_id}")

        return result

    def get_user_jobs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get jobs for a specific user."""
        user_jobs_key = f"{self.user_jobs_prefix}{user_id}"
        job_ids = self.redis_client.lrange(user_jobs_key, offset, offset + limit - 1)

        jobs = []
        for job_id in job_ids:
            job_data = self.get_job(job_id)
            if job_data:
                jobs.append(job_data)

        return jobs

    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs filtered by status."""
        jobs = []
        cursor = 0

        while len(jobs) < limit:
            cursor, keys = self.redis_client.scan(
                cursor=cursor,
                match=f"{self.job_prefix}*",
                count=100
            )

            for key in keys:
                job_data = self.redis_client.hgetall(key)
                if job_data.get("status") == status:
                    # Parse JSON fields
                    if "options" in job_data:
                        try:
                            job_data["options"] = json.loads(job_data["options"])
                        except json.JSONDecodeError:
                            job_data["options"] = {}

                    if "progress" in job_data:
                        job_data["progress"] = float(job_data["progress"])

                    jobs.append(job_data)

                    if len(jobs) >= limit:
                        break

            if cursor == 0:
                break

        return jobs

    def get_pending_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending jobs."""
        return self.get_jobs_by_status("pending", limit)

    def get_processing_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get currently processing jobs."""
        return self.get_jobs_by_status("processing", limit)

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Clean up jobs older than specified days.

        Args:
            days: Age in days for jobs to be deleted

        Returns:
            Number of jobs deleted
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = self.redis_client.scan(
                cursor=cursor,
                match=f"{self.job_prefix}*",
                count=100
            )

            for key in keys:
                created_at = self.redis_client.hget(key, "created_at")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at)
                        if created_dt.timestamp() < cutoff:
                            self.redis_client.delete(key)
                            deleted_count += 1
                    except ValueError:
                        pass

            if cursor == 0:
                break

        logger.info(f"Cleaned up {deleted_count} old jobs")
        return deleted_count

    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            "pending": len(self.get_jobs_by_status("pending")),
            "processing": len(self.get_jobs_by_status("processing")),
            "completed": len(self.get_jobs_by_status("completed")),
            "failed": len(self.get_jobs_by_status("failed")),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of Redis connection."""
        try:
            self.redis_client.ping()
            info = self.redis_client.info()
            return {
                "status": "healthy",
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
