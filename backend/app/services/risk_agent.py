"""Risk-scoring service for converting detections into a safety risk score."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Optional

import pickle

from app.models.risk import RiskFeatureInput, RiskScore, RiskScoreResponse

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml_models" / "risk_model.pkl"


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert arbitrary values to floats while guarding against invalid inputs."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_model(model_path: Optional[str | Path] = None) -> Optional[Any]:
    """Load a serialized model if one exists; otherwise return None to use rule-based scoring."""
    target = Path(model_path) if model_path is not None else MODEL_PATH
    if not target.exists():
        return None

    try:
        with open(target, "rb") as model_file:
            return pickle.load(model_file)
    except Exception:
        return None


def _rule_based_score(features: RiskFeatureInput) -> RiskScore:
    """Compute a transparent score from the current feature set when no trained model is available."""
    base = 0.12
    score = base
    score += min(features.traffic_density * 0.35, 0.30)
    score += min(features.pedestrian_count * 0.04, 0.18)
    score += min(features.vehicle_count * 0.015, 0.15)
    score += min(features.pothole_count * 0.12, 0.18)
    score += min(features.speed_kmh / 200.0 * 0.20, 0.20)
    score += min(features.weather_risk * 0.25, 0.25)
    score += min((1.0 - features.road_quality) * 0.20, 0.20)
    if features.night_mode:
        score += 0.10
    if "pothole" in [item.lower() for item in features.critical_objects]:
        score += 0.10
    if "pedestrian" in [item.lower() for item in features.critical_objects]:
        score += 0.05

    score = max(0.0, min(score, 1.0))
    if score < 0.25:
        severity = "low"
    elif score < 0.5:
        severity = "moderate"
    elif score < 0.75:
        severity = "high"
    else:
        severity = "critical"

    confidence = 0.72 if score < 0.5 else 0.84
    factors = {
        "traffic_density": round(min(features.traffic_density * 1.0, 1.0), 4),
        "pedestrian_count": round(min(features.pedestrian_count * 0.04, 1.0), 4),
        "vehicle_count": round(min(features.vehicle_count * 0.015, 1.0), 4),
        "pothole_count": round(min(features.pothole_count * 0.12, 1.0), 4),
        "speed_kmh": round(min(features.speed_kmh / 200.0, 1.0), 4),
        "weather_risk": round(min(features.weather_risk, 1.0), 4),
        "road_quality": round(max(0.0, 1.0 - features.road_quality), 4),
    }

    recommendations = []
    if score >= 0.50:
        recommendations.append("Reduce speed and increase following distance.")
    if features.pothole_count > 0:
        recommendations.append("Alert road maintenance unit about observed potholes.")
    if features.pedestrian_count > 0:
        recommendations.append("Increase pedestrian awareness and slow down near walkways.")
    if not recommendations:
        recommendations.append("Continue normal monitoring; current conditions remain stable.")

    return RiskScore(
        score=round(score, 4),
        severity=severity,
        confidence=round(confidence, 4),
        factors=factors,
        recommendations=recommendations,
    )


def compute_risk(features: Dict[str, Any] | RiskFeatureInput) -> RiskScore:
    """Return a risk score from either raw feature dicts or validated input models."""
    feature_payload = features if isinstance(features, RiskFeatureInput) else RiskFeatureInput(**features)
    model = _load_model()

    if model is not None:
        try:
            prediction = model.predict([[
                feature_payload.traffic_density,
                feature_payload.pedestrian_count,
                feature_payload.vehicle_count,
                feature_payload.pothole_count,
                feature_payload.speed_kmh,
                feature_payload.weather_risk,
                feature_payload.road_quality,
                1.0 if feature_payload.night_mode else 0.0,
            ]])[0]
            risk_score = float(prediction)
            if not math.isnan(risk_score):
                score = max(0.0, min(risk_score, 1.0))
                severity = "low" if score < 0.25 else "moderate" if score < 0.5 else "high" if score < 0.75 else "critical"
                return RiskScore(
                    score=round(score, 4),
                    severity=severity,
                    confidence=0.9,
                    factors={"model_prediction": round(score, 4)},
                    recommendations=["Model-based risk assessment used."]
                )
        except Exception:
            pass

    return _rule_based_score(feature_payload)


def build_risk_response(camera_id: str, features: Dict[str, Any] | RiskFeatureInput) -> RiskScoreResponse:
    """Create a final API response object from a detected scene and its features."""
    feature_payload = features if isinstance(features, RiskFeatureInput) else RiskFeatureInput(camera_id=camera_id, **features)
    risk = compute_risk(feature_payload)
    return RiskScoreResponse(
        camera_id=camera_id,
        risk=risk,
        summary=f"Road risk for {camera_id} is {risk.severity} with a score of {risk.score:.2f}.",
        timestamp=None,
    )
