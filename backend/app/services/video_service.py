"""Video management service for RealityShield-AI."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, HTTPException
import boto3
import mimetypes
import cv2
import tempfile
import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor

class VideoMetadata:
    """Video metadata model."""

    def __init__(self, video_id: str, filename: str, original_filename: str,
                 file_path: str, file_size: int, file_type: str,
                 uploaded_by: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.id = video_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.file_type = file_type
        self.uploaded_by = uploaded_by
        self.uploaded_at = datetime.now(timezone.utc)
        self.metadata = metadata or {}
        self.status = "uploading"
        self.processing_progress = 0
        self.processing_error = None
        self.analysis_results = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat(),
            "status": self.status,
            "processing_progress": self.processing_progress,
            "processing_error": self.processing_error,
            "analysis_results": self.analysis_results,
            "metadata": self.metadata
        }


class VideoStorageConfig:
    """Video storage configuration."""

    def __init__(self):
        self.local_upload_dir = Path("uploads/videos")
        self.max_file_size_mb = 100
        self.allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.bmp'}
        self.allowed_mime_types = {
            'video/mp4': '.mp4',
            'video/x-msvideo': '.avi',
            'video/quicktime': '.mov',
            'video/x-matroska': '.mkv',
            'video/webm': '.webm',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/bmp': '.bmp'
        }

        # S3 configuration
        self.s3_client = None
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "realityshield-videos")
        self.s3_prefix = "videos"

        self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client if credentials are available."""
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")

        if aws_access_key and aws_secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )

    def validate_file(self, filename: str, file_size: int, content_type: Optional[str] = None) -> List[str]:
        """Validate video file and return list of errors."""
        errors = []

        # Check filename
        if not filename:
            errors.append("No filename provided")
            return errors

        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            errors.append(f"Unsupported file type: {file_ext}. Allowed: {', '.join(self.allowed_extensions)}")

        # Check file size
        if file_size > (self.max_file_size_mb * 1024 * 1024):
            errors.append(f"File too large: {file_size / (1024*1024):.1f}MB. Maximum: {self.max_file_size_mb}MB")

        # Check content type if provided
        if content_type:
            expected_ext = self.allowed_mime_types.get(content_type)
            if expected_ext and file_ext != expected_ext:
                errors.append(f"File extension {file_ext} doesn't match content type {content_type}")

        return errors

    def generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename to avoid collisions."""
        file_ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_ext}"


class VideoService:
    """Service for managing video uploads, storage, and metadata."""

    def __init__(self, storage_config: Optional[VideoStorageConfig] = None):
        self.storage_config = storage_config or VideoStorageConfig()
        self.video_metadata_db = {}  # In-memory storage, should use database in production
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def upload_video(self, file: UploadFile, user_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Upload and process video file."""
        try:
            # Validate file
            file_ext = Path(file.filename).suffix.lower()
            file_size = await file.seekable().__sizeof__() if hasattr(file, '__sizeof__') else 0

            validation_errors = self.storage_config.validate_file(file.filename, file_size, file.content_type)
            if validation_errors:
                raise HTTPException(status_code=400, detail="; ".join(validation_errors))

            # Generate unique filename
            filename = self.storage_config.generate_unique_filename(file.filename)
            video_id = str(uuid.uuid4())

            # Read file content
            file_content = await file.read()

            # Save video file
            file_path = await self._save_video_file(filename, file_content)

            # Create metadata
            video_metadata = VideoMetadata(
                video_id=video_id,
                filename=filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=len(file_content),
                file_type=file_ext,
                uploaded_by=user_id,
                metadata=metadata or {}
            )

            # Save metadata to database
            await self._save_metadata(video_metadata)

            # Start video processing
            asyncio.create_task(self._process_video(video_metadata))

            return {
                "success": True,
                "video_id": video_id,
                "filename": filename,
                "metadata": video_metadata.to_dict(),
                "message": "Video uploaded successfully"
            }

        except Exception as e:
            # Cleanup on error
            if 'filename' in locals() and self.storage_config.local_upload_dir.exists():
                try:
                    video_file = self.storage_config.local_upload_dir / filename
                    if video_file.exists():
                        video_file.unlink()
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

    async def _save_video_file(self, filename: str, content: bytes) -> str:
        """Save video file to local storage or S3."""
        file_path = self.storage_config.local_upload_dir / filename

        # Ensure directory exists
        self.storage_config.local_upload_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)

        # Upload to S3 if configured
        if self.storage_config.s3_client:
            try:
                self.storage_config.s3_client.upload_file(
                    str(file_path),
                    self.storage_config.bucket_name,
                    f"{self.storage_config.s3_prefix}/{filename}",
                    ExtraArgs={
                        'ContentType': mimetypes.guess_type(str(file_path))[0] or 'video/mp4',
                        'Metadata': {
                            'uploaded_at': datetime.utcnow().isoformat(),
                            'uploaded_by': 'system'
                        }
                    }
                )
            except Exception as e:
                # Log S3 error but don't fail the operation
                print(f"S3 upload failed: {e}")

        return str(file_path)

    async def _save_metadata(self, metadata: VideoMetadata):
        """Save video metadata to database."""
        # In production, this would save to a real database
        self.video_metadata_db[metadata.id] = metadata

    async def get_video_info(self, video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata by ID."""
        return self.video_metadata_db.get(video_id)

    async def update_video_status(self, video_id: str, status: str,
                                 progress: int = None, error: str = None,
                                 results: Dict[str, Any] = None):
        """Update video processing status."""
        metadata = self.video_metadata_db.get(video_id)
        if metadata:
            metadata.status = status
            if progress is not None:
                metadata.processing_progress = progress
            if error:
                metadata.processing_error = error
            if results:
                metadata.analysis_results = results

    async def _process_video(self, metadata: VideoMetadata):
        """Process video for analysis (placeholder)."""
        try:
            metadata.status = "processing"
            await self._save_metadata(metadata)

            # Simulate video processing
            await asyncio.sleep(1)  # Simulate processing time

            # Update progress
            for progress in [25, 50, 75, 100]:
                await asyncio.sleep(0.5)
                await self.update_video_status(metadata.id, "processing", progress)

            # Simulate analysis results
            analysis_results = {
                "duration": 120.5,
                "frame_count": 1800,
                "objects_detected": [
                    {"class": "car", "count": 15},
                    {"class": "pedestrian", "count": 8},
                    {"class": "bike", "count": 3},
                    {"class": "pothole", "count": 2}
                ],
                "risk_score": 0.35,
                "severity": "low"
            }

            await self.update_video_status(
                metadata.id,
                "completed",
                100,
                results=analysis_results
            )

        except Exception as e:
            await self.update_video_status(metadata.id, "failed", error=str(e))

    async def list_videos(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List uploaded videos."""
        videos = []
        for metadata in self.video_metadata_db.values():
            if user_id is None or metadata.uploaded_by == user_id:
                videos.append(metadata.to_dict())
        return videos

    async def delete_video(self, video_id: str) -> bool:
        """Delete video and metadata."""
        metadata = self.video_metadata_db.pop(video_id, None)
        if metadata:
            try:
                # Delete local file
                video_file = Path(metadata.file_path)
                if video_file.exists():
                    video_file.unlink()

                # Delete from S3 if exists
                if self.storage_config.s3_client:
                    try:
                        self.storage_config.s3_client.delete_object(
                            Bucket=self.storage_config.bucket_name,
                            Key=f"{self.storage_config.s3_prefix}/{Path(metadata.filename).name}"
                        )
                    except Exception:
                        pass  # Ignore S3 deletion errors

                return True
            except Exception:
                return False
        return False


# Global video service instance
video_service = VideoService()