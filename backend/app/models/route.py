"""Route recommendation data models for navigation safety analysis."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteSegment:
    """Represents one segment in a proposed route."""
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    risk_score: float = 0.0


@dataclass
class RouteRecommendation:
    """Stores candidate safe routes for comparison."""
    routes: List[RouteSegment] = field(default_factory=list)
    best_route_id: Optional[str] = None
