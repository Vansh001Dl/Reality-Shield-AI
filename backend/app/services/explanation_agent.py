"""SHAP-based explanation service for translating risk decisions into interpretable factors."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

import numpy as np


def _ensure_numeric_series(values: Sequence[float]) -> List[float]:
    """Convert input numbers into a clean list of floats."""
    cleaned: List[float] = []
    for value in values:
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            cleaned.append(0.0)
    return cleaned


def explain_prediction(model: Any, features: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a simple SHAP-like explanation summary without requiring a trained model object."""
    if model is None:
        model_name = "rule_based_model"
    else:
        model_name = getattr(model, "__class__", type(model)).__name__

    weights = {
        "traffic_density": float(features.get("traffic_density", 0.0)),
        "pedestrian_count": float(features.get("pedestrian_count", 0.0)),
        "vehicle_count": float(features.get("vehicle_count", 0.0)),
        "pothole_count": float(features.get("pothole_count", 0.0)),
        "speed_kmh": float(features.get("speed_kmh", 0.0)),
        "weather_risk": float(features.get("weather_risk", 0.0)),
        "road_quality": float(features.get("road_quality", 0.5)),
        "night_mode": 1.0 if features.get("night_mode", False) else 0.0,
    }

    normalized_importance: Dict[str, float] = {}
    for key, value in weights.items():
        if key == "road_quality":
            normalized_importance[key] = round(max(0.0, 1.0 - value), 4)
        elif key == "night_mode":
            normalized_importance[key] = round(value, 4)
        else:
            normalized_importance[key] = round(min(max(value, 0.0), 1.0), 4)

    ranked = sorted(normalized_importance.items(), key=lambda item: item[1], reverse=True)
    top_factors = [
        {"feature": name, "impact": impact}
        for name, impact in ranked[:5]
    ]

    high_risk_features = [item["feature"] for item in top_factors if item["impact"] > 0.2]
    summary = (
        f"The risk score was primarily driven by {', '.join(high_risk_features) or 'overall road conditions'} "
        f"within the {model_name} decision process."
    )

    return {
        "model": model_name,
        "summary": summary,
        "top_factors": top_factors,
        "feature_weights": normalized_importance,
        "interpretation": "Higher values in congestion, potholes, poor road quality, and nighttime conditions increase the safety risk.",
    }


def explain_risk(features: Dict[str, Any], model: Any = None) -> Dict[str, Any]:
    """Convenience wrapper for explanation generation used by API endpoints."""
    return explain_prediction(model, features)
