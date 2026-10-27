"""SHAP explainability endpoints for interpretable risk decisions."""

from typing import Any, Dict

from fastapi import APIRouter

from app.services.explanation_agent import explain_risk

router = APIRouter(prefix="/explain", tags=["explainability"])


@router.get("/summary")
def explain_summary() -> Dict[str, str]:
    """Return a service ready response for the explanation module."""
    return {"status": "ready", "service": "explanation_agent"}


@router.post("/summary")
def explain_risk_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a SHAP-like explanation summary for a given risk feature set."""
    explanation = explain_risk(payload)
    return {
        "status": "ok",
        "explanation": explanation,
    }
