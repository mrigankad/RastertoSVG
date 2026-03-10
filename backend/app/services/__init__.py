"""Core services for conversion, preprocessing, and optimization.

Phase 7 additions: AI Engine, Smart Engine Selector, AI Preprocessing, DiffVG Optimizer.
"""

from app.services.converter import Converter
from app.services.preprocessor import Preprocessor
from app.services.optimizer import SVGOptimizer
from app.services.vtracer_engine import VTracerEngine
from app.services.potrace_engine import PotraceEngine
from app.services.edge_detector import EdgeDetector
from app.services.line_smoother import LineSmoother
from app.services.quality_analyzer import QualityAnalyzer
from app.services.file_manager import FileManager
from app.services.job_tracker import JobTracker

# Phase 7: AI-Powered Vectorization Engine
from app.services.smart_engine_selector import SmartEngineSelector
from app.services.ai_preprocessing import AIPreprocessingPipeline
from app.services.diffvg_optimizer import SVGPathOptimizer
from app.services.ai_engine import AIVectorizationEngine

__all__ = [
    # Core services
    "Converter",
    "Preprocessor",
    "SVGOptimizer",
    "VTracerEngine",
    "PotraceEngine",
    "EdgeDetector",
    "LineSmoother",
    "QualityAnalyzer",
    "FileManager",
    "JobTracker",
    # Phase 7: AI Engine
    "SmartEngineSelector",
    "AIPreprocessingPipeline",
    "SVGPathOptimizer",
    "AIVectorizationEngine",
]
