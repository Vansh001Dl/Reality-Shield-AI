"""Pydantic schemas for road object detection results and frame metadata."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """Represents a detected object with a unique tracking identifier when available."""

    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: List[float] = Field(default_factory=list)
    track_id: Optional[int] = None
    frame_index: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DetectionResponse(BaseModel):
    """Contains the list of detections and metadata for a processed frame or video."""

    detections: List[Detection] = Field(default_factory=list)
    frame_metadata: Dict[str, Any] = Field(default_factory=dict)
