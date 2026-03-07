"""API routes for image conversion."""

import logging
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from app.api.models import (
    BatchConversionRequest,
    BatchConversionResponse,
    ConversionRequest,
    ConversionResponse,
    HealthCheck,
    JobStatus,
    UploadResponse,
)
from app.config import settings
from app.services.file_manager import FileManager
from app.services.job_tracker import JobTracker
from app.services.quality_analyzer import QualityAnalyzer
from app.workers.tasks import batch_convert_task, convert_image_task

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
file_manager = FileManager()
job_tracker = JobTracker()
quality_analyzer = QualityAnalyzer()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload an image file for conversion.

    Returns a file_id that can be used for conversion requests.
    """
    # Validate content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    try:
        # Save file
        result = await file_manager.save_upload(file)

        return UploadResponse(
            file_id=result["file_id"],
            filename=result["filename"],
            size=result["size"],
            format=result["content_type"],
        )

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, f"Failed to save file: {e}")


@router.post("/convert", response_model=ConversionResponse)
async def convert_image(
    file_id: str = Form(...),
    image_type: str = Form("auto"),
    quality_mode: str = Form("standard"),
    color_palette: int = Form(32),
    denoise_strength: str = Form("medium"),
) -> ConversionResponse:
    """
    Start a conversion job for an uploaded image.

    Returns a job_id to track conversion status.
    """
    # Validate file exists
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    # Validate parameters
    if image_type not in ["auto", "color", "monochrome"]:
        raise HTTPException(400, "Invalid image_type. Use: auto, color, monochrome")

    if quality_mode not in ["fast", "standard", "high"]:
        raise HTTPException(400, "Invalid quality_mode. Use: fast, standard, high")

    # Prepare options
    options = {
        "image_type": image_type,
        "quality_mode": quality_mode,
        "color_palette": color_palette,
        "denoise_strength": denoise_strength,
    }

    try:
        # Create job
        job_id = job_tracker.create_job(file_id, options)

        # Queue conversion task
        task = convert_image_task.delay(job_id)

        logger.info(f"Created conversion job: {job_id} for file: {file_id}")

        from datetime import datetime, timezone, timezone
        return ConversionResponse(
            job_id=job_id,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(500, f"Failed to create conversion job: {e}")


@router.post("/compare")
async def compare_quality(file_id: str = Form(...)):
    """
    Run all three quality modes and return comparison.
    
    Useful for users to understand trade-offs between quality modes.
    """
    # Validate file exists
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        # Create jobs for all three quality modes
        job_ids = {}
        
        for quality in ["fast", "standard", "high"]:
            options = {
                "image_type": "auto",
                "quality_mode": quality,
                "color_palette": 32 if quality == "standard" else (16 if quality == "fast" else 64),
                "denoise_strength": "medium",
            }
            
            job_id = job_tracker.create_job(file_id, options)
            convert_image_task.delay(job_id)
            job_ids[quality] = job_id
        
        logger.info(f"Created comparison jobs for file: {file_id}")

        return {
            "comparison_id": file_id,
            "jobs": job_ids,
            "message": "All three quality modes queued. Poll individual job statuses for results.",
        }

    except Exception as e:
        logger.error(f"Failed to create comparison: {e}")
        raise HTTPException(500, f"Failed to create comparison: {e}")


@router.post("/recommend")
async def recommend_quality(file_id: str = Form(...)):
    """
    Analyze image and recommend optimal quality mode.
    """
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        recommendation = quality_analyzer.get_recommendation(str(upload_path))
        return recommendation
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(500, f"Failed to analyze image: {e}")


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Get current status and progress of a conversion job."""
    job_data = job_tracker.get_job(job_id)

    if not job_data:
        raise HTTPException(404, "Job not found")

    from datetime import datetime, timezone

    # Parse dates
    created_at = job_data.get("created_at")
    if created_at:
        created_at = datetime.fromisoformat(created_at)

    completed_at = job_data.get("completed_at")
    if completed_at:
        completed_at = datetime.fromisoformat(completed_at)

    processing_time = job_data.get("processing_time")

    return JobStatus(
        job_id=job_data["job_id"],
        status=job_data["status"],
        progress=job_data.get("progress", 0.0),
        error=job_data.get("error"),
        result_url=job_data.get("result_url"),
        created_at=created_at,
        completed_at=completed_at,
        processing_time=processing_time,
    )


@router.get("/result/{job_id}")
async def download_result(job_id: str):
    """Download the completed SVG file."""
    # Check job status first
    job_data = job_tracker.get_job(job_id)

    if not job_data:
        raise HTTPException(404, "Job not found")

    if job_data["status"] == "failed":
        error_msg = job_data.get("error", "Unknown error")
        raise HTTPException(400, f"Conversion failed: {error_msg}")

    if job_data["status"] != "completed":
        raise HTTPException(400, f"Conversion not complete. Status: {job_data['status']}")

    # Get result file
    result_path = file_manager.get_result(job_id)

    if not result_path or not result_path.exists():
        raise HTTPException(404, "Result file not found")

    return FileResponse(
        path=str(result_path),
        media_type="image/svg+xml",
        filename=f"{job_id}.svg",
    )


@router.get("/result/{job_id}/stats")
async def get_result_stats(job_id: str):
    """Get statistics about a conversion result."""
    result_path = file_manager.get_result(job_id)
    
    if not result_path or not result_path.exists():
        raise HTTPException(404, "Result not found")
    
    try:
        from app.services.optimizer import SVGOptimizer
        optimizer = SVGOptimizer()
        
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stats = optimizer.get_stats(content)
        return stats
    except Exception as e:
        raise HTTPException(500, f"Failed to analyze result: {e}")


@router.post("/batch", response_model=BatchConversionResponse)
async def batch_convert(request: BatchConversionRequest) -> BatchConversionResponse:
    """
    Start multiple conversion jobs.

    Returns a batch_id and list of job_ids.
    """
    import uuid
    from datetime import datetime, timezone

    # Validate all files exist
    for file_id in request.file_ids:
        if not file_manager.get_upload(file_id):
            raise HTTPException(404, f"File not found: {file_id}")

    batch_id = str(uuid.uuid4())

    try:
        # Queue batch task
        task = batch_convert_task.delay(
            batch_id=batch_id,
            file_ids=request.file_ids,
            options=request.options.dict(),
        )

        # Create job IDs for immediate response
        job_ids = []
        for file_id in request.file_ids:
            job_id = job_tracker.create_job(file_id, request.options.dict())
            job_ids.append(job_id)
            # Queue individual conversion
            convert_image_task.delay(job_id)

        logger.info(f"Created batch: {batch_id} with {len(job_ids)} jobs")

        return BatchConversionResponse(
            batch_id=batch_id,
            job_ids=job_ids,
            total=len(job_ids),
        )

    except Exception as e:
        logger.error(f"Failed to create batch: {e}")
        raise HTTPException(500, f"Failed to create batch: {e}")


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List conversion jobs."""
    if status:
        jobs = job_tracker.get_jobs_by_status(status, limit)
    else:
        # Get all jobs (limited)
        jobs = []
        for s in ["pending", "processing", "completed", "failed"]:
            jobs.extend(job_tracker.get_jobs_by_status(s, limit // 4))
            if len(jobs) >= limit:
                break
        jobs = jobs[:limit]

    return {
        "jobs": jobs,
        "count": len(jobs),
        "limit": limit,
        "offset": offset,
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files."""
    job_data = job_tracker.get_job(job_id)

    if not job_data:
        raise HTTPException(404, "Job not found")

    # Delete result file if exists
    file_manager.delete_result(job_id)

    # Delete job record
    job_tracker.delete_job(job_id)

    logger.info(f"Deleted job: {job_id}")

    return {"status": "deleted", "job_id": job_id}


@router.get("/storage/stats")
async def get_storage_stats():
    """Get storage usage statistics."""
    return file_manager.get_storage_stats()


@router.post("/storage/cleanup")
async def cleanup_storage(
    days: int = Query(30, ge=1, le=365),
    background_tasks: BackgroundTasks = None,
):
    """Clean up old files."""
    from app.workers.tasks import cleanup_old_files_task

    # Run cleanup in background
    cleanup_old_files_task.delay(days)

    return {
        "status": "cleanup_started",
        "days": days,
        "message": "Cleanup task queued",
    }


@router.get("/queue/stats")
async def get_queue_stats():
    """Get job queue statistics."""
    return job_tracker.get_queue_stats()


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    from datetime import datetime, timezone

    # Check Redis
    redis_health = job_tracker.get_health_status()

    # Check engines
    from app.services.converter import Converter
    converter = Converter()
    engine_info = converter.get_engine_info()

    status = "healthy" if redis_health["connected"] else "unhealthy"

    return HealthCheck(
        status=status,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all services."""
    from app.services.converter import Converter
    from app.workers.tasks import health_check_task

    # Run health check task
    result = health_check_task.delay()
    health_data = result.get(timeout=10)

    return health_data
