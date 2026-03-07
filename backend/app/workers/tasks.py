"""Celery tasks for async image processing."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from app.config import settings
from app.services.converter import Converter
from app.services.file_manager import FileManager
from app.services.job_tracker import JobTracker
from app.workers.celery import celery_app

logger = logging.getLogger(__name__)

# Initialize services
file_manager = FileManager()
job_tracker = JobTracker()


@celery_app.task(bind=True, name="convert_image")
def convert_image_task(self, job_id: str):
    """
    Main conversion task executed by Celery workers.

    Args:
        job_id: ID of the job to process
    """
    logger.info(f"Starting conversion for job {job_id}")

    try:
        # Get job data
        job_data = job_tracker.get_job(job_id)
        if not job_data:
            raise ValueError(f"Job not found: {job_id}")

        file_id = job_data.get("file_id")
        options = job_data.get("options", {})

        # Update status to processing
        job_tracker.update_job(job_id, status="processing", progress=0.1)
        logger.info(f"Job {job_id}: Processing file {file_id}")

        # Get uploaded file
        upload_path = file_manager.get_upload(file_id)
        if not upload_path:
            raise FileNotFoundError(f"Upload not found: {file_id}")

        logger.info(f"Job {job_id}: Found upload at {upload_path}")

        # Prepare output path
        date_dir = datetime.now().strftime("%Y%m%d")
        result_subdir = Path(settings.RESULT_DIR) / date_dir
        result_subdir.mkdir(parents=True, exist_ok=True)
        output_path = result_subdir / f"{job_id}.svg"

        # Update progress
        job_tracker.update_job(job_id, progress=0.3)
        self.update_state(state="PROCESSING", meta={"progress": 0.3})

        # Perform conversion
        converter = Converter()
        result = converter.convert(
            input_path=str(upload_path),
            output_path=str(output_path),
            image_type=options.get("image_type", "auto"),
            quality_mode=options.get("quality_mode", "standard"),
        )

        logger.info(f"Job {job_id}: Conversion completed")

        # Update progress
        job_tracker.update_job(job_id, progress=0.8)
        self.update_state(state="PROCESSING", meta={"progress": 0.8})

        # Save metadata
        metadata = {
            "job_id": job_id,
            "file_id": file_id,
            "conversion_result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        import json
        meta_path = result_subdir / f"{job_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)

        # Update job as completed
        result_url = f"/api/v1/result/{job_id}"
        job_tracker.update_job(
            job_id=job_id,
            status="completed",
            progress=1.0,
            result_url=result_url,
            processing_time=result.get("processing_time", 0),
        )

        logger.info(f"Job {job_id}: Completed successfully")

        return {
            "status": "success",
            "job_id": job_id,
            "result_url": result_url,
            "processing_time": result.get("processing_time", 0),
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Job {job_id}: Time limit exceeded")
        job_tracker.update_job(
            job_id=job_id,
            status="failed",
            error="Processing time limit exceeded",
            progress=0.0,
        )
        raise

    except Exception as e:
        logger.error(f"Job {job_id}: Conversion failed: {e}")

        # Update job as failed
        job_tracker.update_job(
            job_id=job_id,
            status="failed",
            error=str(e),
            progress=0.0,
        )

        # Retry logic
        retry_count = self.request.retries
        max_retries = 3

        if retry_count < max_retries:
            logger.info(f"Job {job_id}: Retrying ({retry_count + 1}/{max_retries})")
            raise self.retry(countdown=60 * (retry_count + 1), exc=e)

        raise


@celery_app.task(bind=True, name="batch_convert")
def batch_convert_task(self, batch_id: str, file_ids: list, options: dict):
    """
    Batch conversion task.

    Args:
        batch_id: Unique batch identifier
        file_ids: List of file IDs to convert
        options: Conversion options
    """
    total = len(file_ids)
    job_ids = []
    completed = 0
    failed = 0

    logger.info(f"Starting batch {batch_id} with {total} files")

    for i, file_id in enumerate(file_ids):
        try:
            # Create individual job
            job_id = job_tracker.create_job(file_id, options)
            job_ids.append(job_id)

            # Queue conversion task
            convert_image_task.delay(job_id)

            logger.info(f"Batch {batch_id}: Queued job {job_id} for file {file_id}")

        except Exception as e:
            logger.error(f"Batch {batch_id}: Failed to queue file {file_id}: {e}")
            failed += 1

        # Update batch progress
        progress = (i + 1) / total
        self.update_state(
            state="PROCESSING",
            meta={
                "batch_id": batch_id,
                "progress": progress,
                "completed": completed,
                "failed": failed,
                "total": total,
            }
        )

    logger.info(f"Batch {batch_id}: Queued {len(job_ids)} jobs")

    return {
        "status": "success",
        "batch_id": batch_id,
        "job_ids": job_ids,
        "total": total,
        "failed": failed,
    }


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files_task(days: int = 30):
    """
    Cleanup old uploaded and result files.

    Args:
        days: Age in days for files to be deleted
    """
    logger.info(f"Starting cleanup of files older than {days} days")

    # Cleanup files
    file_stats = file_manager.cleanup_old_files(days)

    # Cleanup jobs
    job_count = job_tracker.cleanup_old_jobs(days)

    logger.info(
        f"Cleanup complete: {file_stats['deleted_upload_dirs']} upload dirs, "
        f"{file_stats['deleted_result_dirs']} result dirs, {job_count} jobs"
    )

    return {
        "deleted_upload_dirs": file_stats["deleted_upload_dirs"],
        "deleted_result_dirs": file_stats["deleted_result_dirs"],
        "deleted_jobs": job_count,
    }


@celery_app.task(name="generate_storage_report")
def generate_storage_report_task():
    """Generate storage usage report."""
    stats = file_manager.get_storage_stats()
    queue_stats = job_tracker.get_queue_stats()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": stats,
        "queue": queue_stats,
    }

    logger.info(f"Storage report: {stats}")
    logger.info(f"Queue stats: {queue_stats}")

    return report


@celery_app.task(name="health_check")
def health_check_task():
    """Perform health check on services."""
    from app.services.converter import Converter

    converter = Converter()
    engine_info = converter.get_engine_info()

    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "redis": job_tracker.get_health_status(),
        "engines": engine_info,
        "storage": file_manager.get_storage_stats(),
    }

    # Overall status
    healthy = (
        health["redis"]["connected"] and
        any(e["available"] for e in engine_info.values())
    )

    health["status"] = "healthy" if healthy else "degraded"

    return health
