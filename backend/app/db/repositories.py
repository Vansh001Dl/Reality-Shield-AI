"""Persistence helpers for video jobs, detections, risk summaries, and alerts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from app.db import database as db_module
from app.db.models import AlertRecord, DetectionRecord, RiskAssessment, RouteAnalysis, VideoJob


def _get_session_factory():
    """Ensure the database session factory is initialized before use."""
    if db_module.SessionLocal is None:
        db_module.init_db()
    return db_module.SessionLocal


def save_video_job(payload: Dict[str, Any]) -> VideoJob:
    """Persist a new video analysis job and return the ORM instance."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        job = VideoJob(**payload)
        session.add(job)
        session.commit()
        session.refresh(job)
        return job


def update_video_job(job_id: str, **updates: Any) -> Optional[VideoJob]:
    """Update a job record with the provided field updates."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        job = session.get(VideoJob, job_id)
        if job is None:
            return None
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        session.commit()
        session.refresh(job)
        return job


def get_video_job(job_id: str) -> Optional[VideoJob]:
    """Fetch one job by its unique job identifier."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        return session.get(VideoJob, job_id)


def list_video_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the newest job records as dictionaries."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        rows = session.query(VideoJob).order_by(desc(VideoJob.created_at)).limit(limit).all()
    return [
        {
            "id": row.id,
            "file_name": row.file_name,
            "status": row.status,
            "progress": row.progress,
            "phase": row.phase,
            "location_label": row.location_label,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


def save_detection_record(payload: Dict[str, Any]) -> DetectionRecord:
    """Store a single detection record for a job."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        row = DetectionRecord(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_detection_records(job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Load recent detections tied to a single processing job."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(DetectionRecord)
            .filter(DetectionRecord.job_id == job_id)
            .order_by(desc(DetectionRecord.created_at))
            .limit(limit)
            .all()
        )
    return [
        {
            "id": row.id,
            "job_id": row.job_id,
            "frame_index": row.frame_index,
            "class_name": row.class_name,
            "confidence": row.confidence,
            "bbox_json": row.bbox_json,
            "track_id": row.track_id,
            "timestamp_utc": row.timestamp_utc.isoformat() if row.timestamp_utc else None,
        }
        for row in rows
    ]


def save_risk_assessment(payload: Dict[str, Any]) -> RiskAssessment:
    """Persist a risk assessment result for a video job."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        row = RiskAssessment(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_latest_risk_assessment(job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the newest risk assessment for a given job."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        row = (
            session.query(RiskAssessment)
            .filter(RiskAssessment.job_id == job_id)
            .order_by(desc(RiskAssessment.created_at))
            .first()
        )
        if row is None:
            return None
    return {
        "id": row.id,
        "job_id": row.job_id,
        "camera_id": row.camera_id,
        "score": row.score,
        "severity": row.severity,
        "confidence": row.confidence,
        "factors_json": row.factors_json,
        "summary": row.summary,
        "model_version": row.model_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def save_route_analysis(payload: Dict[str, Any]) -> RouteAnalysis:
    """Persist a route analysis result tied to a job or route request."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        row = RouteAnalysis(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def save_alert_record(payload: Dict[str, Any]) -> AlertRecord:
    """Store a safety alert generated from risk or hazard analysis."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        row = AlertRecord(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent alert records in descending timestamp order."""
    session_factory = _get_session_factory()
    with session_factory() as session:
        rows = session.query(AlertRecord).order_by(desc(AlertRecord.created_at)).limit(limit).all()
    return [
        {
            "id": row.id,
            "job_id": row.job_id,
            "alert_type": row.alert_type,
            "level": row.level,
            "message": row.message,
            "acknowledged": bool(row.acknowledged),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
