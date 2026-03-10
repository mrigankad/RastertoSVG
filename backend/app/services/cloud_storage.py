"""Cloud storage service — Phase 9.

Provides an abstraction layer for S3-compatible object storage:
- Upload files to cloud storage
- Generate presigned download URLs
- Manage user storage quotas
- Local filesystem fallback for development
"""

import hashlib
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)


class StorageConfig:
    """Storage configuration."""
    def __init__(self):
        self.provider = os.getenv("STORAGE_PROVIDER", "local")  # "local", "s3", "r2"
        self.bucket_name = os.getenv("STORAGE_BUCKET", "raster-svg-uploads")
        self.region = os.getenv("STORAGE_REGION", "us-east-1")
        self.endpoint_url = os.getenv("STORAGE_ENDPOINT_URL", None)
        self.access_key = os.getenv("STORAGE_ACCESS_KEY", None)
        self.secret_key = os.getenv("STORAGE_SECRET_KEY", None)
        self.cdn_base_url = os.getenv("STORAGE_CDN_URL", None)
        self.local_base_path = Path(os.getenv("STORAGE_LOCAL_PATH", "./storage/cloud"))
        self.presigned_url_expiry = int(os.getenv("STORAGE_URL_EXPIRY", "3600"))


_config = StorageConfig()


class CloudStorageService:
    """Unified cloud storage service supporting S3, R2, and local filesystem."""

    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or _config
        self._s3_client = None

        if self.config.provider == "local":
            self.config.local_base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using local storage: {self.config.local_base_path}")

    def _get_s3_client(self):
        """Lazy-load S3 client."""
        if self._s3_client is None and self.config.provider in ("s3", "r2"):
            try:
                import boto3
                kwargs = {
                    "region_name": self.config.region,
                }
                if self.config.endpoint_url:
                    kwargs["endpoint_url"] = self.config.endpoint_url
                if self.config.access_key:
                    kwargs["aws_access_key_id"] = self.config.access_key
                    kwargs["aws_secret_access_key"] = self.config.secret_key

                self._s3_client = boto3.client("s3", **kwargs)
                logger.info(f"S3 client initialized for {self.config.provider}")
            except ImportError:
                logger.warning("boto3 not installed, falling back to local storage")
                self.config.provider = "local"
                self.config.local_base_path.mkdir(parents=True, exist_ok=True)
        return self._s3_client

    # =========================================================================
    # Upload
    # =========================================================================

    def upload_file(
        self,
        file_data: BinaryIO,
        storage_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Upload a file to storage.
        
        Args:
            file_data: File-like object to upload
            storage_key: Storage path/key (e.g., "users/{id}/inputs/image.png")
            content_type: MIME type
            metadata: Optional metadata dict
        
        Returns:
            {"key": str, "size": int, "etag": str, "url": str}
        """
        if self.config.provider == "local":
            return self._upload_local(file_data, storage_key, content_type)
        else:
            return self._upload_s3(file_data, storage_key, content_type, metadata)

    def _upload_local(self, file_data: BinaryIO, key: str, content_type: str) -> dict:
        dest = self.config.local_base_path / key
        dest.parent.mkdir(parents=True, exist_ok=True)

        content = file_data.read()
        dest.write_bytes(content)
        
        return {
            "key": key,
            "size": len(content),
            "etag": hashlib.md5(content).hexdigest(),
            "url": f"/storage/{key}",
        }

    def _upload_s3(self, file_data: BinaryIO, key: str, content_type: str, metadata: Optional[dict]) -> dict:
        client = self._get_s3_client()
        if not client:
            return self._upload_local(file_data, key, content_type)

        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        client.upload_fileobj(file_data, self.config.bucket_name, key, ExtraArgs=extra_args)
        
        # Get object metadata
        head = client.head_object(Bucket=self.config.bucket_name, Key=key)
        
        return {
            "key": key,
            "size": head.get("ContentLength", 0),
            "etag": head.get("ETag", "").strip('"'),
            "url": self.get_url(key),
        }

    # =========================================================================
    # Download / URL
    # =========================================================================

    def get_url(self, storage_key: str, expires_in: Optional[int] = None) -> str:
        """Get a URL for accessing a stored file."""
        if self.config.cdn_base_url:
            return f"{self.config.cdn_base_url}/{storage_key}"

        if self.config.provider == "local":
            return f"/storage/{storage_key}"
        
        client = self._get_s3_client()
        if not client:
            return f"/storage/{storage_key}"

        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.config.bucket_name, "Key": storage_key},
            ExpiresIn=expires_in or self.config.presigned_url_expiry,
        )

    def get_file(self, storage_key: str) -> Optional[bytes]:
        """Download a file from storage."""
        if self.config.provider == "local":
            path = self.config.local_base_path / storage_key
            if path.exists():
                return path.read_bytes()
            return None
        
        client = self._get_s3_client()
        if not client:
            return None
        
        try:
            response = client.get_object(Bucket=self.config.bucket_name, Key=storage_key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to download {storage_key}: {e}")
            return None

    # =========================================================================
    # Delete
    # =========================================================================

    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage."""
        if self.config.provider == "local":
            path = self.config.local_base_path / storage_key
            if path.exists():
                path.unlink()
                return True
            return False
        
        client = self._get_s3_client()
        if not client:
            return False
        
        try:
            client.delete_object(Bucket=self.config.bucket_name, Key=storage_key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {storage_key}: {e}")
            return False

    def delete_prefix(self, prefix: str) -> int:
        """Delete all files under a prefix (e.g., "users/{id}/")."""
        if self.config.provider == "local":
            path = self.config.local_base_path / prefix
            if path.exists() and path.is_dir():
                count = sum(1 for _ in path.rglob("*") if _.is_file())
                shutil.rmtree(path)
                return count
            return 0
        
        client = self._get_s3_client()
        if not client:
            return 0

        count = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix):
            objects = page.get("Contents", [])
            if objects:
                client.delete_objects(
                    Bucket=self.config.bucket_name,
                    Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
                )
                count += len(objects)
        return count

    # =========================================================================
    # Storage Stats
    # =========================================================================

    def get_user_storage_usage(self, user_id: str) -> dict:
        """Get storage usage for a user."""
        prefix = f"users/{user_id}/"

        if self.config.provider == "local":
            path = self.config.local_base_path / prefix
            if not path.exists():
                return {"total_bytes": 0, "file_count": 0}
            
            total = 0
            count = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
                    count += 1
            return {"total_bytes": total, "file_count": count}
        
        client = self._get_s3_client()
        if not client:
            return {"total_bytes": 0, "file_count": 0}

        total = 0
        count = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                total += obj.get("Size", 0)
                count += 1

        return {"total_bytes": total, "file_count": count}

    def generate_storage_key(self, user_id: str, category: str, filename: str) -> str:
        """Generate a unique storage key for a file.
        
        Example: users/abc123/inputs/1710000000_image.png
        """
        timestamp = int(time.time())
        safe_name = filename.replace(" ", "_").replace("/", "_")
        return f"users/{user_id}/{category}/{timestamp}_{safe_name}"


# Singleton
_storage: Optional[CloudStorageService] = None


def get_cloud_storage() -> CloudStorageService:
    global _storage
    if _storage is None:
        _storage = CloudStorageService()
    return _storage
