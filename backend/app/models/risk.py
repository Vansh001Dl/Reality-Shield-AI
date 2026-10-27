"""Pydantic schemas for safety risk evaluation inputs and outputs."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskFeatureInput(BaseModel):
    """Expected feature payload produced from vision detections and environment metadata."""

    camera_id: str = "cam_01"
    traffic_density: float = Field(default=0.0, ge=0.0, le=1.0)
    pedestrian_count: int = Field(default=0, ge=0)
    vehicle_count: int = Field(default=0, ge=0)
    pothole_count: int = Field(default=0, ge=0)
    speed_kmh: float = Field(default=0.0, ge=0.0, le=200.0)
    weather_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    road_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    night_mode: bool = False
    critical_objects: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskScore(BaseModel):
    """Structured risk score with severity and contributing factors."""

    score: float = Field(..., ge=0.0, le=1.0)
    severity: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    factors: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class RiskScoreResponse(BaseModel):
    """API response returned by the risk agent."""

    camera_id: str
    risk: RiskScore
    summary: str
    timestamp: Optional[str] = None
