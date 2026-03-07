"""File management service for uploads and results."""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file storage for uploads and conversion results."""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.result_dir = Path(settings.RESULT_DIR)
        self.max_file_size = settings.MAX_IMAGE_SIZE

        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> Dict[str, any]:
        """
        Save an uploaded file and return file metadata.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Dictionary with file_id, path, size, and format
        """
        # Generate unique file ID
        file_id = str(uuid4())

        # Determine file extension
        original_filename = file.filename or "unknown"
        extension = Path(original_filename).suffix.lower()

        # Validate extension
        valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
        if extension not in valid_extensions:
            raise ValueError(f"Unsupported file format: {extension}")

        # Create date-based directory structure
        date_dir = datetime.now().strftime("%Y%m%d")
        upload_subdir = self.upload_dir / date_dir
        upload_subdir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = upload_subdir / f"{file_id}{extension}"

        try:
            # Read and validate size
            content = await file.read()
            file_size = len(content)

            if file_size > self.max_file_size:
                raise ValueError(
                    f"File too large: {file_size} bytes (max: {self.max_file_size} bytes)"
                )

            if file_size == 0:
                raise ValueError("File is empty")

            # Write to disk
            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"Saved upload: {file_id} ({file_size} bytes)")

            return {
                "file_id": file_id,
                "filename": original_filename,
                "path": str(file_path),
                "size": file_size,
                "extension": extension,
                "content_type": file.content_type,
            }

        except Exception as e:
            # Clean up on failure
            if file_path.exists():
                file_path.unlink()
            raise

    def save_result(self, job_id: str, svg_content: str, metadata: Optional[Dict] = None) -> str:
        """
        Save conversion result SVG.

        Args:
            job_id: Unique job identifier
            svg_content: SVG file content
            metadata: Optional metadata dictionary

        Returns:
            Path to saved result
        """
        # Create date-based directory structure
        date_dir = datetime.now().strftime("%Y%m%d")
        result_subdir = self.result_dir / date_dir
        result_subdir.mkdir(parents=True, exist_ok=True)

        # Save SVG
        svg_path = result_subdir / f"{job_id}.svg"
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        # Save metadata if provided
        if metadata:
            import json
            meta_path = result_subdir / f"{job_id}.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Saved result: {job_id}")
        return str(svg_path)

    def get_upload(self, file_id: str) -> Optional[Path]:
        """Get path to uploaded file by file_id."""
        # Search in upload directories
        for date_dir in self.upload_dir.iterdir():
            if date_dir.is_dir():
                for file_path in date_dir.iterdir():
                    if file_path.stem == file_id:
                        return file_path
        return None

    def get_result(self, job_id: str) -> Optional[Path]:
        """Get path to result SVG by job_id."""
        # Search in result directories
        for date_dir in self.result_dir.iterdir():
            if date_dir.is_dir():
                svg_path = date_dir / f"{job_id}.svg"
                if svg_path.exists():
                    return svg_path
        return None

    def get_result_metadata(self, job_id: str) -> Optional[Dict]:
        """Get result metadata by job_id."""
        for date_dir in self.result_dir.iterdir():
            if date_dir.is_dir():
                meta_path = date_dir / f"{job_id}.json"
                if meta_path.exists():
                    import json
                    with open(meta_path, "r", encoding="utf-8") as f:
                        return json.load(f)
        return None

    def get_result_with_metadata(self, job_id: str) -> Tuple[Optional[Path], Optional[Dict]]:
        """Get both result path and metadata."""
        result_path = self.get_result(job_id)
        metadata = self.get_result_metadata(job_id)
        return result_path, metadata

    def delete_upload(self, file_id: str) -> bool:
        """Delete an uploaded file."""
        file_path = self.get_upload(file_id)
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted upload: {file_id}")
            return True
        return False

    def delete_result(self, job_id: str) -> bool:
        """Delete a result and its metadata."""
        deleted = False

        # Find and delete SVG
        for date_dir in self.result_dir.iterdir():
            if date_dir.is_dir():
                svg_path = date_dir / f"{job_id}.svg"
                if svg_path.exists():
                    svg_path.unlink()
                    deleted = True

                # Delete metadata if exists
                meta_path = date_dir / f"{job_id}.json"
                if meta_path.exists():
                    meta_path.unlink()

        if deleted:
            logger.info(f"Deleted result: {job_id}")

        return deleted

    def cleanup_old_files(self, days: int = 30) -> Dict[str, int]:
        """
        Remove files older than specified days.

        Args:
            days: Age in days for files to be deleted

        Returns:
            Dictionary with counts of deleted files
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted_uploads = 0
        deleted_results = 0

        # Clean up uploads
        for date_dir in self.upload_dir.iterdir():
            if date_dir.is_dir():
                dir_time = datetime.fromtimestamp(date_dir.stat().st_mtime)
                if dir_time < cutoff:
                    shutil.rmtree(date_dir)
                    deleted_uploads += 1
                    logger.info(f"Cleaned up upload directory: {date_dir}")

        # Clean up results
        for date_dir in self.result_dir.iterdir():
            if date_dir.is_dir():
                dir_time = datetime.fromtimestamp(date_dir.stat().st_mtime)
                if dir_time < cutoff:
                    shutil.rmtree(date_dir)
                    deleted_results += 1
                    logger.info(f"Cleaned up result directory: {date_dir}")

        return {
            "deleted_upload_dirs": deleted_uploads,
            "deleted_result_dirs": deleted_results,
        }

    def get_storage_stats(self) -> Dict[str, any]:
        """Get storage statistics."""
        total_upload_size = 0
        total_upload_count = 0
        total_result_size = 0
        total_result_count = 0

        # Calculate upload stats
        for date_dir in self.upload_dir.iterdir():
            if date_dir.is_dir():
                for file_path in date_dir.iterdir():
                    if file_path.is_file():
                        total_upload_size += file_path.stat().st_size
                        total_upload_count += 1

        # Calculate result stats
        for date_dir in self.result_dir.iterdir():
            if date_dir.is_dir():
                for file_path in date_dir.iterdir():
                    if file_path.is_file():
                        total_result_size += file_path.stat().st_size
                        total_result_count += 1

        return {
            "uploads": {
                "count": total_upload_count,
                "size_bytes": total_upload_size,
                "size_mb": round(total_upload_size / (1024 * 1024), 2),
            },
            "results": {
                "count": total_result_count,
                "size_bytes": total_result_size,
                "size_mb": round(total_result_size / (1024 * 1024), 2),
            },
            "total_size_mb": round((total_upload_size + total_result_size) / (1024 * 1024), 2),
        }
