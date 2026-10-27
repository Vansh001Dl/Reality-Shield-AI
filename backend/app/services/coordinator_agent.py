"""Multi-agent orchestration for road safety detection, scoring, explanation, and route planning."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.explanation_agent import explain_risk
from app.services.risk_agent import compute_risk
from app.services.route_agent import recommend_route


def _normalize_detections(detections: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count detections by class so the risk model can build a scene summary."""
    summary = {
        "car": 0,
        "truck": 0,
        "bus": 0,
        "bike": 0,
        "pedestrian": 0,
        "pothole": 0,
    }
    for item in detections or []:
        key = str(item.get("class_name", "")).lower()
        if key in summary:
            summary[key] += 1
    return summary


def _build_risk_features(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Construct the feature dict for the risk agent from detection data and scene inputs."""
    detections = payload.get("detections", [])
    counts = _normalize_detections(detections)
    return {
        "camera_id": payload.get("camera_id", "cam_01"),
        "traffic_density": payload.get("traffic_density", min(1.0, (counts["car"] + counts["truck"] + counts["bus"]) / 20.0)),
        "pedestrian_count": counts["pedestrian"],
        "vehicle_count": counts["car"] + counts["truck"] + counts["bus"],
        "pothole_count": counts["pothole"],
        "speed_kmh": payload.get("speed_kmh", 50.0),
        "weather_risk": payload.get("weather_risk", 0.2),
        "road_quality": payload.get("road_quality", 0.6),
        "night_mode": payload.get("night_mode", False),
        "critical_objects": payload.get("critical_objects", [obj for obj in counts if counts[obj] > 0]),
        "metadata": payload.get("metadata", {}),
    }


def _build_route_candidates(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build route options from the incoming payload or fallback to a default route list."""
    routes = payload.get("routes")
    if routes:
        return routes

    base = payload.get("route_base", {"lat": 31.5204, "lon": 74.3587})
    return [
        {
            "route_id": "safe_route",
            "traffic_density": 0.2,
            "congestion": 0.1,
            "potholes": 0.1,
            "speed_limit": 60,
            "pedestrian_risk": 0.1,
            "weather_risk": 0.1,
            "origin": base,
        },
        {
            "route_id": "riskier_route",
            "traffic_density": 0.8,
            "congestion": 0.7,
            "potholes": 0.8,
            "speed_limit": 40,
            "pedestrian_risk": 0.7,
            "weather_risk": 0.5,
            "origin": base,
        },
    ]


def run_pipeline(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrate the full AI workflow: detection -> risk -> explanation -> route selection."""
    feature_set = _build_risk_features(input_data)
    risk_result = compute_risk(feature_set)
    explanation = explain_risk(feature_set)
    route_result = recommend_route(_build_route_candidates(input_data))

    return {
        "status": "ok",
        "camera_id": feature_set["camera_id"],
        "risk": {
            "score": risk_result.score,
            "severity": risk_result.severity,
            "confidence": risk_result.confidence,
            "recommendations": risk_result.recommendations,
        },
        "explanation": explanation,
        "recommended_route": route_result.get("recommended_route"),
        "route_candidates": route_result.get("all_routes", []),
        "summary": (
            f"Camera {feature_set['camera_id']} is currently in a {risk_result.severity} risk state. "
            f"The safest route suggestion is {route_result.get('recommended_route', {}).get('route_id', 'default_route')}"
        ),
    }
