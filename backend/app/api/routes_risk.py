"""Safety risk score endpoints for road and environment evaluation."""

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter

from app.models.risk import RiskFeatureInput, RiskScoreResponse, RiskScore
from app.services.risk_agent import build_risk_response

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/score")
def risk_score() -> Dict[str, str]:
    """Return a simple health check response for the risk service."""
    return {"status": "ready", "service": "risk_agent"}


@router.post("/score", response_model=RiskScoreResponse)
def score_risk(payload: RiskFeatureInput) -> RiskScoreResponse:
    """Score the current road scene and return a structured risk assessment."""
    response = build_risk_response(payload.camera_id, payload)
    response.timestamp = datetime.now(timezone.utc).isoformat()
    return response


@router.get("/score/{camera_id}")
def score_risk_mock(camera_id: str) -> Dict[str, object]:
    """Return a mocked risk summary for a given camera until live risk streaming is connected."""
    return {
        "camera_id": camera_id,
        "risk": RiskScore(
            score=0.18,
            severity="low",
            confidence=0.75,
            factors={"traffic_density": 0.2},
            recommendations=["Monitor the road scene and continue routine checks."],
        ).model_dump(),
        "status": "stub",
    }
