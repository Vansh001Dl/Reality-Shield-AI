"""Weather data proxy for the recorded-video dashboard location."""

from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current")
def current_weather(
    latitude: float = Query(28.6139, ge=-90, le=90),
    longitude: float = Query(77.209, ge=-180, le=180),
) -> Dict[str, Any]:
    """Return current conditions from Open-Meteo without browser CORS dependency."""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "hourly": "precipitation_probability",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=8,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="Weather provider unavailable") from error