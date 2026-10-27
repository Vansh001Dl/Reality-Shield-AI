"""Local SQLite persistence for recorded-video analytics history."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "video_history.sqlite3"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS video_analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_name TEXT NOT NULL,
    location_name TEXT,
    total_detections INTEGER NOT NULL DEFAULT 0,
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    pedestrian_count INTEGER NOT NULL DEFAULT 0,
    pothole_count INTEGER NOT NULL DEFAULT 0,
    risk_score REAL NOT NULL DEFAULT 0,
    severity TEXT NOT NULL,
    route_risk REAL NOT NULL DEFAULT 0
)
"""


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(_CREATE_TABLE)
    connection.commit()
    return connection


def save_history(payload: Dict[str, Any]) -> int:
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO video_analysis_history
            (source_name, location_name, total_detections, vehicle_count, pedestrian_count, pothole_count, risk_score, severity, route_risk)
            VALUES (:source_name, :location_name, :total_detections, :vehicle_count, :pedestrian_count, :pothole_count, :risk_score, :severity, :route_risk)
            """,
            payload,
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_history(limit: int = 20) -> List[Dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM video_analysis_history ORDER BY analyzed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
