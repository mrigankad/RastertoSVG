"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ConversionRequest(BaseModel):
    """Request model for image conversion."""

    image_type: Literal["auto", "color", "monochrome"] = Field(
        default="auto",
        description="Type of image processing to use",
    )
    quality_mode: Literal["fast", "standard", "high"] = Field(
        default="standard",
        description="Quality mode for conversion",
    )
    color_palette: Optional[int] = Field(
        default=32,
        ge=8,
        le=256,
        description="Maximum colors for color reduction",
    )
    denoise_strength: Optional[str] = Field(
        default="medium",
        description="Denoising strength: light, medium, heavy",
    )


class ConversionResponse(BaseModel):
    """Response model for conversion request."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Job creation timestamp")


class JobStatus(BaseModel):
    """Model for job status information."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        ..., description="Current job status"
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Progress from 0.0 to 1.0",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if job failed",
    )
    result_url: Optional[str] = Field(
        default=None,
        description="URL to download result",
    )
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Job completion timestamp",
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Processing time in seconds",
    )


class UploadResponse(BaseModel):
    """Response model for file upload."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Detected image format")


class BatchConversionRequest(BaseModel):
    """Request model for batch conversion."""

    file_ids: list[str] = Field(..., description="List of file IDs to convert")
    options: ConversionRequest = Field(
        default_factory=ConversionRequest,
        description="Conversion options",
    )


class BatchConversionResponse(BaseModel):
    """Response model for batch conversion."""

    batch_id: str = Field(..., description="Unique batch identifier")
    job_ids: list[str] = Field(..., description="List of job IDs")
    total: int = Field(..., description="Total number of jobs")


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Check timestamp",
    )
