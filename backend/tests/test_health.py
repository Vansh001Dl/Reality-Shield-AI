from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_is_available():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "RealityShield-AI"
    assert payload["status"] in {"healthy", "degraded"}


def test_versioned_health_endpoint_is_available():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "RealityShield-AI"


def test_readiness_endpoint_reports_checks():
    response = client.get("/api/ready")
    assert response.status_code == 200
    payload = response.json()
    assert "ready" in payload
    assert "checks" in payload


def test_video_jobs_endpoint_is_available():
    response = client.get("/api/detect/video/jobs", params={"limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["jobs"], list)
