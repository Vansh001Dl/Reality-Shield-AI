"""SQLAlchemy models for video jobs, detections, alerts, and risk records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


def utc_now() -> datetime:
    """Use timezone-aware UTC timestamps for all persisted records."""
    return datetime.now(timezone.utc)


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(String(64), primary_key=True)
    file_name = Column(String(255), nullable=False)
    dataset_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    phase = Column(String(128), nullable=False, default="queued")
    location_label = Column(String(255), nullable=False, default="unknown")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source_path = Column(String(512), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    detections = relationship("DetectionRecord", back_populates="job", cascade="all, delete-orphan")
    assessments = relationship("RiskAssessment", back_populates="job", cascade="all, delete-orphan")
    alerts = relationship("AlertRecord", back_populates="job", cascade="all, delete-orphan")


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), ForeignKey("video_jobs.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False, default=0)
    class_name = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    bbox_json = Column(JSON, nullable=False, default=list)
    track_id = Column(Integer, nullable=True, index=True)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job = relationship("VideoJob", back_populates="detections")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), ForeignKey("video_jobs.id"), nullable=False, index=True)
    camera_id = Column(String(128), nullable=False, default="recorded_video")
    score = Column(Float, nullable=False, default=0.0)
    severity = Column(String(32), nullable=False, default="unknown")
    confidence = Column(Float, nullable=False, default=0.0)
    factors_json = Column(JSON, nullable=False, default=dict)
    summary = Column(Text, nullable=True)
    model_version = Column(String(128), nullable=False, default="rule_based_v1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job = relationship("VideoJob", back_populates="assessments")


class RouteAnalysis(Base):
    __tablename__ = "route_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), ForeignKey("video_jobs.id"), nullable=True, index=True)
    start_label = Column(String(255), nullable=False)
    end_label = Column(String(255), nullable=False)
    recommended_route = Column(JSON, nullable=False, default=dict)
    alternatives_json = Column(JSON, nullable=False, default=list)
    risk_score = Column(Float, nullable=False, default=0.0)
    travel_time_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), ForeignKey("video_jobs.id"), nullable=True, index=True)
    alert_type = Column(String(64), nullable=False, default="risk")
    level = Column(String(32), nullable=False, default="info")
    message = Column(Text, nullable=False)
    acknowledged = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job = relationship("VideoJob", back_populates="alerts")
