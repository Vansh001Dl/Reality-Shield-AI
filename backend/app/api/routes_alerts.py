"""Alerts and notifications endpoints for safety events."""

from typing import Any, Dict, List
from datetime import datetime, timezone

from fastapi import APIRouter


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/recent")
def recent_alerts() -> Dict[str, List[Dict[str, Any]] | str]:
    """Return persisted alert records; no alert store is configured yet."""
    return {"status": "ok", "alerts": []}


@router.post("/trigger")
def trigger_alert(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build an alert from a caller-provided analysis result."""
    risk = payload.get("risk", {})
    camera_id = payload.get("camera_id", "recorded_video")
    risk_severity = risk.get("severity", "unknown")

    alert = {
        "status": "ok",
        "alert": {
            "type": "risk",
            "level": risk_severity,
            "message": f"Safety risk is {risk_severity} for camera {camera_id}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return alert
