"""Route recommendation endpoints for safe navigation planning."""

from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.route_agent import recommend_route

router = APIRouter(prefix="/route", tags=["route"])


@router.get("/recommend")
def route_recommend() -> Dict[str, Any]:
    """Return a simple service-status response for route recommendations."""
    return {"status": "ready", "service": "route_agent"}


@router.post("/recommend")
def compare_routes(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate multiple safe route options and return the best one."""
    routes = payload.get("routes", [])
    return recommend_route(routes)
