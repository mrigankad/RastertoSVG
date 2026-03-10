"""AI-Powered Vectorization Engine — Phase 7 Orchestrator.

Combines all AI components into a unified conversion pipeline:
1. Smart Engine Selection (image analysis → engine routing)
2. AI Preprocessing (noise detection, super-resolution, bg removal)
3. SAM-guided segmentation (semantic region extraction)
4. Engine-specific conversion (VTracer / Potrace)
5. DiffVG-inspired optimization (gradient fills, path simplification)

This is the main entry point for AI-enhanced conversions.
"""

import logging
import time
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.services.smart_engine_selector import (
    EngineType,
    ImageCategory,
    SmartEngineSelector,
    EngineRecommendation,
)
from app.services.ai_preprocessing import AIPreprocessingPipeline
from app.services.diffvg_optimizer import SVGPathOptimizer

logger = logging.getLogger(__name__)


class AIVectorizationEngine:
    """Phase 7: AI-Powered Vectorization Engine.
    
    Provides a complete AI-driven conversion pipeline that:
    - Analyzes the input image and selects the optimal engine
    - Applies intelligent preprocessing (denoise, upscale, enhance)
    - Uses SAM segmentation for complex images (when available)
    - Converts using the selected engine with optimized parameters
    - Post-processes with DiffVG-inspired SVG optimization
    
    Falls back gracefully when AI components are unavailable.
    """

    def __init__(self):
        self.engine_selector = SmartEngineSelector()
        self.ai_preprocessing = AIPreprocessingPipeline()
        self.diffvg_optimizer = SVGPathOptimizer()
        
        # Lazy-load heavy dependencies
        self._sam_vectorizer = None
        self._vtracer = None
        self._potrace = None
        self._ml_converter = None
        
        logger.info("AIVectorizationEngine initialized")

    @property
    def sam_vectorizer(self):
        """Lazy-load SAM vectorizer."""
        if self._sam_vectorizer is None:
            try:
                from app.services.sam_vectorizer import SAMVectorizer
                self._sam_vectorizer = SAMVectorizer()
                if self._sam_vectorizer.is_available():
                    logger.info("SAM vectorizer loaded successfully")
                else:
                    logger.info("SAM dependencies not available, SAM features disabled")
            except ImportError:
                logger.info("SAM vectorizer module not found")
        return self._sam_vectorizer

    @property
    def vtracer(self):
        """Lazy-load VTracer engine."""
        if self._vtracer is None:
            from app.services.vtracer_engine import VTracerEngine
            self._vtracer = VTracerEngine()
        return self._vtracer

    @property
    def potrace(self):
        """Lazy-load Potrace engine."""
        if self._potrace is None:
            from app.services.potrace_engine import PotraceEngine
            self._potrace = PotraceEngine()
        return self._potrace

    def convert(
        self,
        input_path: str,
        output_path: str,
        mode: Literal["auto", "speed", "balanced", "quality", "max_quality"] = "auto",
        engine_override: Optional[str] = None,
        enable_ai_preprocessing: bool = True,
        enable_sam: bool = True,
        enable_optimization: bool = True,
        enable_gradients: bool = True,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """AI-powered image-to-SVG conversion.
        
        Args:
            input_path: Path to input raster image
            output_path: Path for output SVG file
            mode: Quality mode:
                - 'auto': Let AI decide best approach
                - 'speed': Fastest conversion (skip AI features)
                - 'balanced': Good quality with reasonable speed
                - 'quality': High quality with AI enhancements
                - 'max_quality': Maximum quality (all AI features enabled)
            engine_override: Force a specific engine ('potrace', 'vtracer', etc.)
            enable_ai_preprocessing: Enable smart preprocessing
            enable_sam: Enable SAM-guided segmentation
            enable_optimization: Enable DiffVG-inspired post-processing
            enable_gradients: Detect and add SVG gradient fills
            custom_params: Custom engine parameters to merge
            
        Returns:
            Dictionary with conversion results, timing, and metadata
        """
        start_time = time.time()
        result: Dict[str, Any] = {
            "success": False,
            "input_path": input_path,
            "output_path": output_path,
            "mode": mode,
            "timings": {},
            "ai_features": {},
        }
        
        try:
            # === STEP 0: Load & Validate ===
            t0 = time.time()
            image = cv2.imread(input_path)
            if image is None:
                raise ValueError(f"Could not load image: {input_path}")
            
            original_shape = image.shape
            result["original_shape"] = original_shape
            result["timings"]["load"] = time.time() - t0
            
            # === STEP 1: Smart Engine Selection ===
            t1 = time.time()
            force_engine = None
            if engine_override:
                try:
                    force_engine = EngineType(engine_override)
                except ValueError:
                    logger.warning(f"Unknown engine: {engine_override}, using auto")
            
            prefer_speed = mode in ("speed",)
            prefer_quality = mode in ("quality", "max_quality")
            
            recommendation = self.engine_selector.analyze_and_select(
                image,
                prefer_speed=prefer_speed,
                prefer_quality=prefer_quality,
                force_engine=force_engine,
            )
            
            result["engine_recommendation"] = {
                "engine": recommendation.engine.value,
                "confidence": recommendation.confidence,
                "category": recommendation.category.value,
                "reasoning": recommendation.reasoning,
                "alternative": (
                    recommendation.alternative_engine.value 
                    if recommendation.alternative_engine else None
                ),
                "preprocessing_hints": recommendation.preprocessing_hints,
            }
            result["timings"]["analysis"] = time.time() - t1
            
            # === STEP 2: AI Preprocessing ===
            processed_image = image
            if enable_ai_preprocessing and mode not in ("speed",):
                t2 = time.time()
                
                enable_upscale = mode in ("quality", "max_quality")
                enable_bg = False  # Only on explicit request
                
                processed_image, preprocess_meta = self.ai_preprocessing.auto_enhance(
                    image,
                    target_use="vectorization",
                    enable_upscale=enable_upscale,
                    enable_bg_removal=enable_bg,
                    enable_denoise=True,
                    enable_contrast=True,
                    enable_sharpen=True,
                )
                
                result["ai_features"]["preprocessing"] = preprocess_meta
                result["timings"]["ai_preprocessing"] = time.time() - t2
            
            # === STEP 3: SAM Segmentation (optional) ===
            sam_masks = None
            if (
                enable_sam 
                and mode in ("quality", "max_quality")
                and recommendation.engine in (EngineType.SAM_VTRACER, EngineType.SAM_DIFFVG)
            ):
                t3 = time.time()
                sam_masks = self._apply_sam_segmentation(processed_image)
                
                if sam_masks:
                    result["ai_features"]["sam"] = {
                        "masks_generated": len(sam_masks),
                        "available": True,
                    }
                else:
                    result["ai_features"]["sam"] = {
                        "masks_generated": 0,
                        "available": False,
                        "reason": "SAM unavailable or no masks generated",
                    }
                
                result["timings"]["sam_segmentation"] = time.time() - t3
            
            # === STEP 4: Conversion ===
            t4 = time.time()
            
            # Get engine-specific params
            params = recommendation.suggested_params.copy()
            if custom_params:
                params.update(custom_params)
            
            # Route to the appropriate conversion method
            actual_engine = recommendation.engine
            
            if actual_engine in (EngineType.SAM_VTRACER, EngineType.SAM_DIFFVG):
                if sam_masks and len(sam_masks) > 0:
                    conversion_result = self._convert_with_sam(
                        processed_image, output_path, sam_masks, params
                    )
                else:
                    # Fallback to VTracer if SAM isn't available
                    actual_engine = EngineType.VTRACER
                    conversion_result = self._convert_vtracer(
                        processed_image, output_path, params
                    )
            elif actual_engine == EngineType.POTRACE:
                conversion_result = self._convert_potrace(
                    processed_image, output_path, params
                )
            else:
                conversion_result = self._convert_vtracer(
                    processed_image, output_path, params
                )
            
            result["conversion"] = conversion_result
            result["actual_engine"] = actual_engine.value
            result["timings"]["conversion"] = time.time() - t4
            
            # === STEP 5: DiffVG-inspired Optimization ===
            if enable_optimization and mode not in ("speed",):
                t5 = time.time()
                
                output_file = Path(output_path)
                if output_file.exists():
                    svg_content = output_file.read_text(encoding="utf-8")
                    
                    optimized_svg, opt_meta = self.diffvg_optimizer.optimize_svg(
                        svg_content,
                        image,  # Use original as reference
                        enable_gradients=enable_gradients and mode in ("quality", "max_quality"),
                        enable_path_simplification=True,
                        enable_color_quantization=True,
                    )
                    
                    output_file.write_text(optimized_svg, encoding="utf-8")
                    
                    result["ai_features"]["optimization"] = opt_meta
                    result["timings"]["optimization"] = time.time() - t5
            
            # === Final metadata ===
            output_file = Path(output_path)
            if output_file.exists():
                result["output_size_bytes"] = output_file.stat().st_size
                result["success"] = True
            
            result["total_time"] = time.time() - start_time
            
            logger.info(
                f"AI conversion complete: {actual_engine.value} | "
                f"Category: {recommendation.category.value} | "
                f"Confidence: {recommendation.confidence:.0%} | "
                f"Time: {result['total_time']:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"AI conversion failed: {e}", exc_info=True)
            result["error"] = str(e)
            result["total_time"] = time.time() - start_time
            
            # Attempt fallback conversion
            try:
                result = self._fallback_convert(
                    input_path, output_path, result
                )
            except Exception as fallback_error:
                result["fallback_error"] = str(fallback_error)
        
        return result

    def _apply_sam_segmentation(
        self, image: np.ndarray
    ) -> Optional[List[Dict[str, Any]]]:
        """Apply SAM segmentation if available."""
        try:
            if self.sam_vectorizer and self.sam_vectorizer.is_available():
                masks = self.sam_vectorizer.generate_masks(image)
                if masks:
                    # Filter to significant masks (>1% of image area)
                    h, w = image.shape[:2]
                    min_area = h * w * 0.01
                    significant = [
                        m for m in masks
                        if m.get("area", 0) > min_area
                    ]
                    return significant if significant else masks[:10]
            return None
        except Exception as e:
            logger.warning(f"SAM segmentation failed: {e}")
            return None

    def _convert_with_sam(
        self,
        image: np.ndarray,
        output_path: str,
        masks: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert using SAM-guided segmentation.
        
        For each SAM mask:
        1. Extract the masked region
        2. Convert with optimized params for that region type
        3. Merge all SVG groups with proper layering
        """
        h, w = image.shape[:2]
        svg_groups = []
        
        # Sort masks by area (largest first for background → foreground layering)
        sorted_masks = sorted(
            masks, 
            key=lambda m: m.get("area", 0), 
            reverse=True
        )
        
        for i, mask_info in enumerate(sorted_masks[:15]):  # Max 15 regions
            mask = mask_info.get("segmentation")
            if mask is None:
                continue
            
            # Create masked region image
            mask_binary = mask.astype(np.uint8) * 255
            
            # Extract bounding box
            bbox = mask_info.get("bbox", [0, 0, w, h])
            x, y, bw, bh = [int(v) for v in bbox]
            
            # Crop region
            region = image[y:y+bh, x:x+bw].copy()
            region_mask = mask_binary[y:y+bh, x:x+bw]
            
            # Apply mask (white background for non-masked areas)
            if len(region.shape) == 3:
                for c in range(3):
                    region[:, :, c] = np.where(
                        region_mask > 128,
                        region[:, :, c],
                        255
                    )
            
            # Convert this region
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as tmp_in:
                cv2.imwrite(tmp_in.name, region)
                tmp_in_path = tmp_in.name
            
            with tempfile.NamedTemporaryFile(
                suffix=".svg", delete=False
            ) as tmp_out:
                tmp_out_path = tmp_out.name
            
            try:
                # Use VTracer for color regions
                pil_img = Image.fromarray(cv2.cvtColor(region, cv2.COLOR_BGR2RGB))
                vtracer_params = {
                    k: v for k, v in params.items()
                    if k in (
                        "color_precision", "filter_speckle", "corner_threshold",
                        "mode", "hierarchical", "path_precision", "max_iterations"
                    )
                }
                self.vtracer.convert_pillow(
                    pil_img, tmp_out_path, **vtracer_params
                )
                
                # Read SVG and wrap in a translated/clipped group
                tmp_svg = Path(tmp_out_path)
                if tmp_svg.exists():
                    svg_region = tmp_svg.read_text(encoding="utf-8")
                    # Extract path data from SVG
                    import re
                    paths = re.findall(r'<path[^/]*/>', svg_region)
                    
                    if paths:
                        group = (
                            f'<g transform="translate({x},{y})" '
                            f'data-sam-region="{i}" '
                            f'data-area="{mask_info.get("area", 0)}">\n'
                        )
                        group += "\n".join(paths)
                        group += "\n</g>"
                        svg_groups.append(group)
            finally:
                # Cleanup temp files
                Path(tmp_in_path).unlink(missing_ok=True)
                Path(tmp_out_path).unlink(missing_ok=True)
        
        # Build final SVG
        svg_content = self._build_composite_svg(w, h, svg_groups)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(svg_content, encoding="utf-8")
        
        return {
            "engine": "sam_vtracer",
            "regions_processed": len(svg_groups),
            "total_masks": len(masks),
            "output_path": output_path,
            "success": True,
        }

    def _convert_vtracer(
        self,
        image: np.ndarray,
        output_path: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert using VTracer engine."""
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        vtracer_params = {
            k: v for k, v in params.items()
            if k in (
                "color_precision", "filter_speckle", "corner_threshold",
                "mode", "hierarchical", "path_precision", "max_iterations",
                "layer_difference", "length_threshold", "splice_threshold",
                "color_sampling_interval",
            )
        }
        
        result = self.vtracer.convert_pillow(pil_img, output_path, **vtracer_params)
        result["engine"] = "vtracer"
        return result

    def _convert_potrace(
        self,
        image: np.ndarray,
        output_path: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert using Potrace engine."""
        # Convert to grayscale for Potrace
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        pil_img = Image.fromarray(gray)
        
        potrace_params = {
            k: v for k, v in params.items()
            if k in (
                "alphamax", "turdsize", "opticurve",
                "opttolerance", "turnpolicy",
            )
        }
        
        result = self.potrace.convert_pillow(pil_img, output_path, **potrace_params)
        result["engine"] = "potrace"
        return result

    def _build_composite_svg(
        self,
        width: int,
        height: int,
        groups: List[str],
    ) -> str:
        """Build a composite SVG from multiple region groups."""
        svg = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">\n'
            f'  <!-- Generated by AI Vectorization Engine (SAM-guided) -->\n'
            f'  <defs></defs>\n'
        )
        
        for group in groups:
            svg += f"  {group}\n"
        
        svg += "</svg>\n"
        return svg

    def _fallback_convert(
        self,
        input_path: str,
        output_path: str,
        partial_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback conversion using basic VTracer (no AI features)."""
        logger.info("Attempting fallback conversion with basic VTracer")
        
        try:
            image = cv2.imread(input_path)
            if image is None:
                raise ValueError(f"Could not load image: {input_path}")
            
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            result = self.vtracer.convert_pillow(
                pil_img, output_path,
                color_precision=32,
                filter_speckle=3,
            )
            
            partial_result["success"] = True
            partial_result["actual_engine"] = "vtracer_fallback"
            partial_result["conversion"] = result
            partial_result["fallback_used"] = True
            
            output_file = Path(output_path)
            if output_file.exists():
                partial_result["output_size_bytes"] = output_file.stat().st_size
            
        except Exception as e:
            partial_result["fallback_error"] = str(e)
        
        return partial_result

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze an image and return detailed features and recommendations.
        
        This is useful for the frontend to display analysis results
        before the user starts conversion.
        """
        image = cv2.imread(image_path)
        if image is None:
            return {"error": f"Could not load: {image_path}"}
        
        recommendation = self.engine_selector.analyze_and_select(image)
        features = self.engine_selector.extract_features(image)
        noise = self.ai_preprocessing.noise_detector.detect_noise(image)
        
        return {
            "recommendation": {
                "engine": recommendation.engine.value,
                "confidence": recommendation.confidence,
                "category": recommendation.category.value,
                "reasoning": recommendation.reasoning,
                "alternative": (
                    recommendation.alternative_engine.value 
                    if recommendation.alternative_engine else None
                ),
                "estimated_quality": recommendation.estimated_quality,
                "estimated_time": recommendation.estimated_time,
                "suggested_params": recommendation.suggested_params,
                "preprocessing_hints": recommendation.preprocessing_hints,
            },
            "features": {
                "dimensions": f"{features.width}x{features.height}",
                "megapixels": round(features.megapixels, 2),
                "is_grayscale": features.is_grayscale,
                "unique_colors": features.unique_colors,
                "dominant_colors": features.dominant_colors,
                "color_complexity": round(features.color_complexity, 3),
                "edge_density": round(features.edge_density, 4),
                "texture_energy": round(features.texture_energy, 3),
                "noise_level": round(features.noise_level, 3),
                "contour_count": features.contour_count,
            },
            "noise": {
                "noise_score": round(noise.get("noise_score", 0), 3),
                "noise_type": noise.get("noise_type", "unknown"),
                "recommendation": noise.get("recommendation", {}),
            },
            "capabilities": self.get_capabilities(),
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Return current AI engine capabilities."""
        sam_available = False
        try:
            if self.sam_vectorizer:
                sam_available = self.sam_vectorizer.is_available()
        except Exception:
            pass
        
        return {
            "engines": self.engine_selector.get_engine_capabilities(),
            "ai_preprocessing": self.ai_preprocessing.get_capabilities(),
            "diffvg_optimizer": self.diffvg_optimizer.get_capabilities(),
            "sam_available": sam_available,
            "modes": {
                "speed": "Fastest conversion, minimal processing",
                "balanced": "Good quality with smart preprocessing",
                "quality": "High quality with AI enhancements + upscaling",
                "max_quality": "Maximum quality with SAM segmentation + DiffVG optimization",
                "auto": "AI selects the best approach based on image analysis",
            },
        }
