"""FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.advanced_routes import router as advanced_router
from app.api.websocket_routes import router as websocket_router
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Redis URL: {settings.REDIS_URL}")

    # Check services
    try:
        from app.services.converter import Converter

        converter = Converter()
        engine_info = converter.get_engine_info()
        logger.info(f"Engines: {engine_info}")
    except Exception as e:
        logger.warning(f"Could not check engines: {e}")

    try:
        from app.services.job_tracker import JobTracker

        tracker = JobTracker()
        health = tracker.get_health_status()
        logger.info(f"Redis health: {health}")
    except Exception as e:
        logger.warning(f"Could not check Redis: {e}")

    yield

    # Shutdown
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Convert raster images to vector SVG format with advanced preprocessing",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(FileNotFoundError)
async def not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle FileNotFoundError exceptions."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


# Include API routes
app.include_router(router, prefix="/api/v1")
app.include_router(advanced_router, prefix="/api/v1")
app.include_router(websocket_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Convert raster images to vector SVG format",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "upload": "/api/v1/upload",
            "convert": "/api/v1/convert",
            "status": "/api/v1/status/{job_id}",
            "result": "/api/v1/result/{job_id}",
        },
    }


@app.get("/api/v1")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": [
            {"path": "/upload", "method": "POST", "description": "Upload an image"},
            {"path": "/convert", "method": "POST", "description": "Start conversion"},
            {"path": "/status/{job_id}", "method": "GET", "description": "Get job status"},
            {"path": "/result/{job_id}", "method": "GET", "description": "Download result"},
            {"path": "/batch", "method": "POST", "description": "Batch conversion"},
            {"path": "/jobs", "method": "GET", "description": "List jobs"},
            {"path": "/storage/stats", "method": "GET", "description": "Storage stats"},
            {"path": "/queue/stats", "method": "GET", "description": "Queue stats"},
        ],
        "advanced_endpoints": [
            {"path": "/advanced/filters", "method": "GET", "description": "List available preprocessing filters"},
            {"path": "/advanced/preview", "method": "POST", "description": "Generate preprocessing preview"},
            {"path": "/advanced/extract-colors/{file_id}", "method": "POST", "description": "Extract color palette"},
            {"path": "/advanced/analyze/{file_id}", "method": "POST", "description": "Analyze image characteristics"},
            {"path": "/advanced/presets", "method": "GET", "description": "List conversion presets"},
            {"path": "/advanced/convert", "method": "POST", "description": "Enhanced conversion with full control"},
            {"path": "/advanced/compare", "method": "POST", "description": "Compare conversion modes"},
        ],
    }
