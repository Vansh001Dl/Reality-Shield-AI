"""Historical analytics endpoints for recorded-video analyses."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.history_database import list_history, save_history

router = APIRouter(prefix="/analytics", tags=["analytics"])


class VideoHistoryCreate(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=255)
    location_name: str = "Unknown location"
    total_detections: int = Field(default=0, ge=0)
    vehicle_count: int = Field(default=0, ge=0)
    pedestrian_count: int = Field(default=0, ge=0)
    pothole_count: int = Field(default=0, ge=0)
    risk_score: float = Field(default=0, ge=0, le=1)
    severity: str = "unknown"
    route_risk: float = Field(default=0, ge=0, le=1)


@router.post("/history")
def save_video_history(payload: VideoHistoryCreate) -> Dict[str, Any]:
    try:
        return {"status": "saved", "id": save_history(payload.model_dump())}
    except Exception as error:
        raise HTTPException(status_code=503, detail="History database is unavailable") from error


@router.get("/history")
def get_video_history(limit: int = 20) -> Dict[str, Any]:
    limit = max(1, min(limit, 100))
    try:
        return {"status": "ok", "history": list_history(limit)}
    except Exception as error:
        raise HTTPException(status_code=503, detail="History database is unavailable") from error