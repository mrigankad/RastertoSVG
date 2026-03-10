"""Application configuration."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "Raster to SVG Converter"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Storage
    UPLOAD_DIR: Path = Path("./storage/uploads")
    RESULT_DIR: Path = Path("./storage/results")
    MAX_IMAGE_SIZE: int = 50 * 1024 * 1024  # 50MB
    CLEANUP_AGE_DAYS: int = 30

    # Processing
    CONVERSION_TIMEOUT: int = 300  # 5 minutes
    MAX_WORKERS: int = 4

    # Phase 9: Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/raster_svg.db"

    # Phase 9: Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Phase 9: OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_BASE: str = "http://localhost:3000/auth/callback"

    # Phase 9: Cloud Storage
    STORAGE_PROVIDER: str = "local"  # "local", "s3", "r2"
    STORAGE_BUCKET: str = "raster-svg-uploads"
    STORAGE_CDN_URL: str = ""

    # Phase 12: Billing (Stripe)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/billing/success"
    STRIPE_CANCEL_URL: str = "http://localhost:3000/billing/cancel"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.RESULT_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
