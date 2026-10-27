"""Vehicle, pedestrian, and pothole detection endpoints."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from uuid import uuid4

import cv2
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.db.repositories import get_video_job, list_video_jobs, save_video_job, update_video_job
from app.models.detection import DetectionResponse
from app.services.dataset_storage import get_dataset, get_video, list_datasets, save_dataset
from app.services.vision_agent import process_frame, process_video_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detect", tags=["detection"])
_analysis_jobs: Dict[str, Dict[str, Any]] = {}
_analysis_jobs_lock = Lock()
_analysis_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-analysis")
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
SUPPORTED_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS


def _validate_location(location: str, latitude: float, longitude: float) -> None:
    if not location.strip():
        raise HTTPException(status_code=422, detail="Set the video location before starting analysis.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="The confirmed location coordinates are invalid.")


def _extract_video_metadata(video_path: str | Path) -> Dict[str, Any]:
    """Capture basic video metadata such as width, height, duration, and FPS."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"The uploaded video could not be opened for analysis: {video_path}")

    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration_seconds = frame_count / fps if fps > 0 else 0.0
        codec = int(capture.get(cv2.CAP_PROP_FOURCC) or 0)
        return {
            "frame_count": frame_count,
            "fps": round(fps, 3),
            "width": width,
            "height": height,
            "duration_seconds": round(duration_seconds, 3),
            "codec": codec,
        }
    finally:
        capture.release()


def _persist_job_status(job_id: str, **updates: Any) -> None:
    """Mirror in-memory job progress into the database-backed job record."""
    payload = {key: value for key, value in updates.items() if value is not None}
    if not payload:
        return
    try:
        update_video_job(job_id, **payload)
    except Exception:
        logger.warning("Could not persist job updates for %s", job_id, exc_info=True)


def _run_video_analysis(job_id: str, temp_path: str, file_name: str, location: Dict[str, Any]) -> None:
    def update_progress(progress: int, phase: str) -> None:
        with _analysis_jobs_lock:
            job = _analysis_jobs.get(job_id)
            if job:
                job.update(progress=progress, phase=phase)
        _persist_job_status(job_id, progress=progress, phase=phase)
        from app.core.realtime import publish_event_from_worker
        publish_event_from_worker({"type": "detection.progress", "job_id": job_id, "progress": progress, "phase": phase})

    try:
        metadata = _extract_video_metadata(temp_path)
        with _analysis_jobs_lock:
            job = _analysis_jobs.get(job_id)
            if job:
                job["metadata"] = {**job.get("metadata", {}), **metadata}
        _persist_job_status(job_id, metadata=metadata)

        result = process_video_file(temp_path, progress_callback=update_progress)
        dataset = save_dataset(job_id, temp_path, file_name, location, result.model_dump(mode="json"))

        with _analysis_jobs_lock:
            _analysis_jobs[job_id].update(
                status="completed",
                progress=100,
                phase="Analysis complete",
                result=result,
                dataset_id=dataset["dataset_id"],
                dataset={
                    key: dataset[key]
                    for key in ("dataset_id", "source_name", "location", "analyzed_at", "storage_backend")
                    if key in dataset
                },
            )
        _persist_job_status(
            job_id,
            status="completed",
            progress=100,
            phase="Analysis complete",
            dataset_id=dataset.get("dataset_id"),
            metadata={**metadata, "dataset_id": dataset.get("dataset_id")},
        )
        from app.core.realtime import publish_event_from_worker
        publish_event_from_worker({"type": "detection.completed", "job_id": job_id, "status": "completed"})
    except Exception as exc:
        logger.exception("Video analysis job %s failed", job_id)
        with _analysis_jobs_lock:
            if job_id in _analysis_jobs:
                _analysis_jobs[job_id].update(status="failed", phase="Analysis failed", error=str(exc))
        _persist_job_status(job_id, status="failed", phase="Analysis failed", error=str(exc))
        from app.core.realtime import publish_event_from_worker
        publish_event_from_worker({"type": "detection.failed", "job_id": job_id, "status": "failed"})
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("/status")
def detection_status() -> Dict[str, str]:
    """Return the current readiness state of the detection service."""
    return {"status": "ready", "mode": "vision_agent"}


@router.post("/video", response_model=DetectionResponse)
async def detect_video(
    file: UploadFile = File(...),
    location: str = Form(default=""),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
) -> DetectionResponse:
    """Accept an uploaded image or video and return detections for the frame(s)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload an image or video file.")

    if file_extension in SUPPORTED_VIDEO_EXTENSIONS:
        if latitude is None or longitude is None:
            raise HTTPException(status_code=422, detail="Set the video location before starting analysis.")
        _validate_location(location, latitude, longitude)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Video exceeds the {settings.max_file_size_mb} MB upload limit.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension or ".jpg") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        if file_extension.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            frame = cv2.imread(temp_path)
            if frame is None:
                raise HTTPException(status_code=400, detail="The uploaded image could not be decoded.")
            return process_frame(frame, source_name=file.filename)

        _extract_video_metadata(temp_path)
        return process_video_file(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/video/jobs", status_code=202)
async def create_video_analysis_job(
    file: UploadFile = File(...),
    location: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
) -> Dict[str, str]:
    """Start video analysis in a worker so clients can poll real progress."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video type. Upload MP4, AVI, MOV, MKV, or WebM.")

    _validate_location(location, latitude, longitude)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded video is empty.")
    if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Video exceeds the {settings.max_file_size_mb} MB upload limit.",
        )

    temp_dir = Path(tempfile.gettempdir())
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(temp_dir)) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        metadata = _extract_video_metadata(temp_path)
    except Exception as exc:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=400, detail=f"The uploaded video could not be decoded: {exc}") from exc

    job_id = uuid4().hex
    job_payload = {
        "id": job_id,
        "file_name": file.filename,
        "dataset_id": None,
        "status": "queued",
        "progress": 0,
        "phase": "Queued for analysis",
        "location_label": location.strip(),
        "latitude": latitude,
        "longitude": longitude,
        "source_path": temp_path,
        "metadata_json": {
            "source": file.filename,
            "location": {"label": location.strip(), "latitude": latitude, "longitude": longitude},
            "metadata": metadata,
        },
    }
    save_video_job(job_payload)

    with _analysis_jobs_lock:
        _analysis_jobs[job_id] = {
            "job_id": job_id,
            "file_name": file.filename,
            "status": "queued",
            "progress": 0,
            "phase": "Queued for analysis",
            "location": {"label": location.strip(), "latitude": latitude, "longitude": longitude},
            "metadata": metadata,
        }

    location_payload = {"label": location.strip(), "latitude": latitude, "longitude": longitude}
    if settings.celery_enabled:
        from app.core.tasks import process_video_task
        process_video_task.delay(job_id, temp_path, file.filename, location_payload)
    else:
        _analysis_executor.submit(_run_video_analysis, job_id, temp_path, file.filename, location_payload)
    from app.core.realtime import publish_event
    await publish_event({"type": "detection.queued", "job_id": job_id, "status": "queued"})
    return {"job_id": job_id, "status": "queued"}


@router.get("/video/jobs")
def list_video_analysis_jobs(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    """Return recent recorded-video jobs for dashboard polling and status review."""
    rows = list_video_jobs(limit=limit)
    return {
        "status": "ok",
        "jobs": [
            {
                "job_id": row["id"],
                "file_name": row["file_name"],
                "status": row["status"],
                "progress": row["progress"],
                "phase": row["phase"],
                "location": {
                    "label": row["location_label"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                },
                "metadata": row.get("metadata_json") if isinstance(row.get("metadata_json"), dict) else {},
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
            for row in rows
        ],
    }


@router.get("/video/jobs/{job_id}")
def get_video_analysis_job(job_id: str) -> Dict[str, Any]:
    """Return current progress and, when complete, the detections for one job."""
    with _analysis_jobs_lock:
        job = _analysis_jobs.get(job_id)
    if not job:
        stored_job = get_video_job(job_id)
        if not stored_job:
            raise HTTPException(status_code=404, detail="Analysis job not found.")
        job = {
            "job_id": stored_job.id,
            "file_name": stored_job.file_name,
            "status": stored_job.status,
            "progress": stored_job.progress,
            "phase": stored_job.phase,
            "location": {"label": stored_job.location_label, "latitude": stored_job.latitude, "longitude": stored_job.longitude},
            "metadata": stored_job.metadata_json,
            "dataset_id": stored_job.dataset_id,
            "created_at": stored_job.created_at.isoformat() if stored_job.created_at else None,
            "updated_at": stored_job.updated_at.isoformat() if stored_job.updated_at else None,
        }
    return dict(job)


def _validate_dataset_id(dataset_id: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{32}", dataset_id):
        raise HTTPException(status_code=404, detail="Saved video dataset not found.")


@router.get("/video/datasets")
def get_video_datasets(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    """List recent videos and their saved analyses from cloud storage."""
    try:
        return {"status": "ok", "datasets": list_datasets(limit)}
    except Exception as error:
        logger.exception("Unable to list saved video datasets from S3")
        raise HTTPException(
            status_code=503,
            detail="Cloud video archive is unavailable. Check the S3 bucket, AWS credentials, and permissions.",
        ) from error


@router.get("/video/datasets/{dataset_id}")
def get_saved_video_dataset(dataset_id: str) -> Dict[str, Any]:
    """Load a saved dataset and all of its detections."""
    _validate_dataset_id(dataset_id)
    try:
        return get_dataset(dataset_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unable to load saved video dataset %s from S3", dataset_id)
        raise HTTPException(
            status_code=503,
            detail="Saved video data could not be loaded from S3. Check bucket access and permissions.",
        ) from error


@router.get("/video/datasets/{dataset_id}/video")
def stream_saved_video(dataset_id: str, request: Request) -> StreamingResponse:
    """Stream a source video for an archived dataset."""
    _validate_dataset_id(dataset_id)
    try:
        body, media_type, status_code, s3_headers = get_video(
            dataset_id,
            request.headers.get("range"),
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unable to stream saved video dataset %s from S3", dataset_id)
        raise HTTPException(
            status_code=503,
            detail="Saved source video could not be loaded from S3. Check bucket access and permissions.",
        ) from error

    def stream_chunks():
        try:
            yield from body.iter_chunks(chunk_size=1024 * 1024)
        finally:
            body.close()

    headers = {"Accept-Ranges": s3_headers.get("AcceptRanges", "bytes")}
    if "ContentLength" in s3_headers:
        headers["Content-Length"] = str(s3_headers["ContentLength"])
    if "ContentRange" in s3_headers:
        headers["Content-Range"] = s3_headers["ContentRange"]
    return StreamingResponse(
        stream_chunks(),
        media_type=media_type,
        status_code=status_code,
        headers=headers,
    )


@router.get("/live/{camera_id}")
def get_live_detection_summary(camera_id: str) -> Dict[str, object]:
    """Return the latest mock summary for a camera feed until a live integration is added."""
    return {
        "camera_id": camera_id,
        "status": "stub",
        "latest_summary": {
            "total_detections": 0,
            "cars": 0,
            "trucks": 0,
            "buses": 0,
            "bikes": 0,
            "pedestrians": 0,
            "potholes": 0,
        },
        "message": "Live camera integration is still mocked for this phase.",
    }
