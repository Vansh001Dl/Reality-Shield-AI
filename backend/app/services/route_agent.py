"""Route comparison logic for evaluating safer travel paths using risk-aware scoring."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


RouteCandidate = Dict[str, Any]


def _score_route(route: RouteCandidate) -> float:
    """Return a simple risk score for a candidate route based on its metadata."""
    traffic = float(route.get("traffic_density", 0.0))
    congestion = float(route.get("congestion", 0.0))
    potholes = float(route.get("potholes", 0.0))
    speed_limit = float(route.get("speed_limit", 50.0))
    pedestrian_risk = float(route.get("pedestrian_risk", 0.0))
    weather = float(route.get("weather_risk", 0.0))

    score = (
        (traffic * 0.30)
        + (congestion * 0.25)
        + (potholes * 0.25)
        + ((100.0 - min(speed_limit, 100.0)) / 100.0 * 0.10)
        + (pedestrian_risk * 0.20)
        + (weather * 0.15)
    )
    return max(0.0, min(score, 1.0))


def recommend_route(routes: Sequence[RouteCandidate]) -> Dict[str, Any]:
    """Evaluate multiple route candidates and choose the safest route."""
    if not routes:
        return {"recommended_route": None, "status": "no_routes"}

    scored_routes = []
    for index, route in enumerate(routes):
        route_score = _score_route(route)
        scored_routes.append({"index": index, "route": route, "risk_score": route_score})

    safest = min(scored_routes, key=lambda item: item["risk_score"])
    safest_route = safest["route"]
    safest_route["risk_score"] = safest["risk_score"]
    safest_route["route_id"] = safest_route.get("route_id", f"route_{safest['index'] + 1}")

    return {
        "recommended_route": safest_route,
        "all_routes": [
            {"route_id": item["route"].get("route_id", f"route_{item['index'] + 1}"), "risk_score": item["risk_score"]}
            for item in scored_routes
        ],
        "status": "ok",
    }


def build_route_payload(start: str, end: str, lat: float, lon: float, risk_level: float = 0.2) -> Dict[str, Any]:
    """Create a simple route object used for prototype route recommendation logic."""
    return {
        "start": start,
        "end": end,
        "origin": {"lat": lat, "lon": lon},
        "traffic_density": 0.5,
        "congestion": 0.4,
        "potholes": risk_level,
        "speed_limit": 60,
        "pedestrian_risk": risk_level,
        "weather_risk": 0.2,
    }
