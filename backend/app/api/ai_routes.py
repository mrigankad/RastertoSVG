"""API routes for the AI-Powered Vectorization Engine (Phase 7).

Exposes endpoints for:
- Image analysis & engine recommendation
- AI-powered conversion with smart routing
- AI preprocessing (denoise, upscale, bg removal)
- Noise analysis
- Engine capabilities
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.ai_models import (
    AICapabilitiesResponse,
    AIConversionRequest,
    AIConversionResponse,
    AIConversionTimings,
    AIPreprocessingRequest,
    AIPreprocessingResponse,
    BackgroundRemovalRequest,
    BackgroundRemovalResponse,
    ImageAnalysisResponse,
    NoiseAnalysisRequest,
    NoiseAnalysisResponse,
)
from app.config import settings
from app.services.file_manager import FileManager
from app.services.job_tracker import JobTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Engine (Phase 7)"])

# Initialize services
file_manager = FileManager()
job_tracker = JobTracker()

# Lazy-loaded AI engine
_ai_engine = None


def _get_ai_engine():
    """Lazy-load the AI engine (heavy initialization)."""
    global _ai_engine
    if _ai_engine is None:
        from app.services.ai_engine import AIVectorizationEngine

        _ai_engine = AIVectorizationEngine()
        logger.info("AI Vectorization Engine initialized")
    return _ai_engine


# =============================================================================
# Image Analysis
# =============================================================================


@router.post("/analyze/{file_id}", response_model=ImageAnalysisResponse)
async def analyze_image(file_id: str):
    """Analyze an image and get engine recommendations.

    Returns detailed image features (color complexity, edge density,
    texture, noise level) and a confidence-scored engine recommendation
    with suggested parameters and preprocessing hints.
    """
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        engine = _get_ai_engine()
        analysis = engine.analyze_image(str(upload_path))

        if "error" in analysis:
            raise HTTPException(400, analysis["error"])

        return ImageAnalysisResponse(**analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


# =============================================================================
# AI-Powered Conversion
# =============================================================================


@router.post("/convert", response_model=AIConversionResponse)
async def ai_convert(request: AIConversionRequest):
    """Start an AI-powered conversion.

    The AI engine will:
    1. Analyze the image to classify it (logo, photo, line art, etc.)
    2. Select the optimal vectorization engine with confidence score
    3. Apply intelligent preprocessing if needed
    4. Convert using the selected engine with optimized parameters
    5. Post-process with DiffVG-inspired SVG optimization

    Modes:
    - **auto**: AI selects the best approach
    - **speed**: Fastest conversion, minimal AI
    - **balanced**: Good quality with smart preprocessing
    - **quality**: High quality with AI enhancements + upscaling
    - **max_quality**: Maximum quality with SAM + DiffVG optimization
    """
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        engine = _get_ai_engine()

        # Create job
        job_id = str(uuid.uuid4())
        output_dir = Path(settings.RESULT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / "output.svg")

        # Run conversion
        result = engine.convert(
            input_path=str(upload_path),
            output_path=output_path,
            mode=request.mode,
            engine_override=request.engine_override,
            enable_ai_preprocessing=request.enable_ai_preprocessing,
            enable_sam=request.enable_sam,
            enable_optimization=request.enable_optimization,
            enable_gradients=request.enable_gradients,
            custom_params=request.custom_params,
        )

        # Build response
        timings = AIConversionTimings(**result.get("timings", {}))

        ai_features_used = []
        if result.get("ai_features", {}).get("preprocessing"):
            ai_features_used.append("ai_preprocessing")
        if result.get("ai_features", {}).get("sam"):
            ai_features_used.append("sam_segmentation")
        if result.get("ai_features", {}).get("optimization"):
            ai_features_used.append("diffvg_optimization")

        preprocessing_steps = (
            result.get("ai_features", {}).get("preprocessing", {}).get("steps_applied", [])
        )

        rec = result.get("engine_recommendation", {})

        return AIConversionResponse(
            job_id=job_id,
            status="completed" if result.get("success") else "failed",
            engine_used=result.get("actual_engine"),
            category_detected=rec.get("category"),
            confidence=rec.get("confidence"),
            mode=request.mode,
            ai_features_used=ai_features_used,
            preprocessing_steps=preprocessing_steps,
            output_url=f"/api/v1/ai/result/{job_id}" if result.get("success") else None,
            output_size_bytes=result.get("output_size_bytes"),
            timings=timings,
            total_time=result.get("total_time"),
            created_at=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI conversion failed: {e}")
        raise HTTPException(500, f"Conversion failed: {str(e)}")


@router.get("/result/{job_id}")
async def get_ai_result(job_id: str):
    """Download the AI conversion result SVG."""
    result_path = Path(settings.RESULT_DIR) / job_id / "output.svg"

    if not result_path.exists():
        raise HTTPException(404, "Result not found")

    return FileResponse(
        path=str(result_path),
        media_type="image/svg+xml",
        filename=f"ai-converted-{job_id[:8]}.svg",
    )


# =============================================================================
# AI Preprocessing
# =============================================================================


@router.post("/preprocess", response_model=AIPreprocessingResponse)
async def ai_preprocess(request: AIPreprocessingRequest):
    """Apply AI preprocessing without conversion.

    Useful for previewing how AI enhancements will affect the image
    before running conversion. Returns original and processed preview URLs.
    """
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        engine = _get_ai_engine()

        # Load image
        image = cv2.imread(str(upload_path))
        if image is None:
            raise HTTPException(400, "Could not load image")

        original_h, original_w = image.shape[:2]

        # Apply AI preprocessing
        processed, metadata = engine.ai_preprocessing.auto_enhance(
            image,
            target_use="vectorization",
            enable_upscale=request.enable_upscale,
            enable_bg_removal=request.enable_bg_removal,
            enable_denoise=request.enable_denoise,
            enable_contrast=request.enable_contrast,
            enable_sharpen=request.enable_sharpen,
            min_dimension=request.min_dimension,
        )

        # Save previews
        preview_id = str(uuid.uuid4())
        preview_dir = Path(settings.RESULT_DIR) / "ai_previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

        original_path = preview_dir / f"{preview_id}_original.png"
        processed_path = preview_dir / f"{preview_id}_processed.png"

        # Resize for preview (max 800px)
        max_preview = 800
        scale = min(max_preview / max(original_w, original_h), 1.0)
        if scale < 1.0:
            preview_original = cv2.resize(image, (int(original_w * scale), int(original_h * scale)))
        else:
            preview_original = image

        cv2.imwrite(str(original_path), preview_original)

        proc_h, proc_w = processed.shape[:2]
        scale_p = min(max_preview / max(proc_w, proc_h), 1.0)
        if scale_p < 1.0:
            preview_processed = cv2.resize(
                processed, (int(proc_w * scale_p), int(proc_h * scale_p))
            )
        else:
            preview_processed = processed

        cv2.imwrite(str(processed_path), preview_processed)

        processing_time = 0.0
        steps = metadata.get("steps_applied", [])

        return AIPreprocessingResponse(
            preview_id=preview_id,
            file_id=request.file_id,
            original_url=f"/api/v1/ai/preview/{preview_id}/original",
            processed_url=f"/api/v1/ai/preview/{preview_id}/processed",
            steps_applied=steps,
            noise_analysis=metadata.get("noise_analysis"),
            processing_time=processing_time,
            original_size={"width": original_w, "height": original_h},
            processed_size={"width": proc_w, "height": proc_h},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI preprocessing failed: {e}")
        raise HTTPException(500, f"Preprocessing failed: {str(e)}")


@router.get("/preview/{preview_id}/{preview_type}")
async def get_ai_preview(preview_id: str, preview_type: str):
    """Get AI preprocessing preview image."""
    if preview_type not in ("original", "processed"):
        raise HTTPException(400, "Type must be 'original' or 'processed'")

    preview_path = Path(settings.RESULT_DIR) / "ai_previews" / f"{preview_id}_{preview_type}.png"

    if not preview_path.exists():
        raise HTTPException(404, "Preview not found")

    return FileResponse(path=str(preview_path), media_type="image/png")


# =============================================================================
# Background Removal
# =============================================================================


@router.post("/remove-background", response_model=BackgroundRemovalResponse)
async def remove_background(request: BackgroundRemovalRequest):
    """Remove background from an image using AI.

    Methods:
    - **auto**: Automatically detect best method
    - **grabcut**: GrabCut algorithm (best for general images)
    - **color**: Color-based segmentation (best for solid backgrounds)
    - **edge**: Edge-based segmentation (best for high-contrast images)
    """
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        engine = _get_ai_engine()

        image = cv2.imread(str(upload_path))
        if image is None:
            raise HTTPException(400, "Could not load image")

        import time

        start = time.time()

        result, metadata = engine.ai_preprocessing.bg_remover.remove_background(
            image,
            method=request.method,
            threshold=request.threshold,
        )

        processing_time = time.time() - start

        # Save previews
        preview_id = str(uuid.uuid4())
        preview_dir = Path(settings.RESULT_DIR) / "ai_previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(str(preview_dir / f"{preview_id}_original.png"), image)
        cv2.imwrite(str(preview_dir / f"{preview_id}_processed.png"), result)

        return BackgroundRemovalResponse(
            preview_id=preview_id,
            file_id=request.file_id,
            original_url=f"/api/v1/ai/preview/{preview_id}/original",
            processed_url=f"/api/v1/ai/preview/{preview_id}/processed",
            method_used=metadata.get("method", request.method),
            mask_coverage=metadata.get("mask_coverage", 0),
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        raise HTTPException(500, f"Background removal failed: {str(e)}")


# =============================================================================
# Noise Analysis
# =============================================================================


@router.post("/noise-analysis/{file_id}", response_model=NoiseAnalysisResponse)
async def analyze_noise(file_id: str):
    """Analyze image noise levels and get denoising recommendations.

    Returns detailed noise metrics including:
    - Composite noise score (0-1)
    - Noise type classification (gaussian, salt_pepper, uniform, mixed)
    - Recommended denoising method and strength
    """
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")

    try:
        engine = _get_ai_engine()

        image = cv2.imread(str(upload_path))
        if image is None:
            raise HTTPException(400, "Could not load image")

        result = engine.ai_preprocessing.noise_detector.detect_noise(image)

        return NoiseAnalysisResponse(
            file_id=file_id,
            noise_score=result.get("noise_score", 0),
            noise_type=result.get("noise_type", "unknown"),
            laplacian_variance=result.get("laplacian_variance", 0),
            mad_noise=result.get("mad_noise", 0),
            local_noise=result.get("local_noise", 0),
            high_freq_noise=result.get("high_freq_noise", 0),
            recommendation=result.get("recommendation", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Noise analysis failed: {e}")
        raise HTTPException(500, f"Noise analysis failed: {str(e)}")


# =============================================================================
# Capabilities
# =============================================================================


@router.get("/capabilities", response_model=AICapabilitiesResponse)
async def get_ai_capabilities():
    """Get all available AI engine capabilities.

    Returns information about available engines, preprocessing features,
    optimization options, and SAM availability.
    """
    try:
        engine = _get_ai_engine()
        caps = engine.get_capabilities()
        return AICapabilitiesResponse(**caps)
    except Exception as e:
        logger.error(f"Capabilities check failed: {e}")
        raise HTTPException(500, f"Failed to check capabilities: {str(e)}")


@router.get("/engines")
async def get_engines():
    """Get list of available vectorization engines with details."""
    try:
        engine = _get_ai_engine()
        return engine.engine_selector.get_engine_capabilities()
    except Exception as e:
        logger.error(f"Engine listing failed: {e}")
        raise HTTPException(500, f"Failed to list engines: {str(e)}")
