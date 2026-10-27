import asyncio

from fastapi.testclient import TestClient

from app.core.middleware import RateLimitMiddleware
from app.core.realtime import ConnectionManager
from app.db.database import _async_database_url
from app.main import app


def test_versioned_detection_route_is_mounted():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/detect/video/jobs" in paths


def test_metrics_endpoint_exposes_prometheus_format():
    response = TestClient(app).get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "realityshield_http_requests_total" in response.text


def test_async_database_url_selects_async_drivers():
    assert _async_database_url("postgresql+psycopg2://user:pass@host/db") == "postgresql+asyncpg://user:pass@host/db"
    assert _async_database_url("sqlite:///./data.db") == "sqlite+aiosqlite:///./data.db"


def test_rate_limiter_rejects_excess_requests():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    async def ok(request):
        return PlainTextResponse("ok")

    limited = Starlette(routes=[Route("/limited", ok)])
    limited.add_middleware(RateLimitMiddleware, requests_per_window=1, window_seconds=60)
    client = TestClient(limited)
    assert client.get("/limited").status_code == 200
    response = client.get("/limited")
    assert response.status_code == 429
    assert response.headers["Retry-After"]


def test_connection_manager_broadcasts_to_connected_client():
    class Socket:
        def __init__(self):
            self.events = []

        async def send_json(self, event):
            self.events.append(event)

    async def run():
        manager = ConnectionManager()
        socket = Socket()
        manager.connections.add(socket)
        await manager.broadcast({"type": "detection", "job_id": "job-1"})
        assert socket.events == [{"type": "detection", "job_id": "job-1"}]

    asyncio.run(run())
