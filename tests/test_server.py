"""test_server.py: Tests for FastAPI backend server."""
import json
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


def test_health_never_exposes_secrets():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["default_mode"] == "replay"
    assert "keys_configured" in data
    # Ensure boolean indicators only, no secret tokens
    for k, v in data["keys_configured"].items():
        assert isinstance(v, bool), f"Key {k} must be boolean, found {type(v)}"


def test_store_endpoint():
    res = client.get("/api/store")
    assert res.status_code == 200
    data = res.json()
    assert data["store_name"] == "Straive Demo Bookstore"
    assert "bays" in data
    assert len(data["bays"]) >= 16


def test_scan_endpoint_f3():
    res = client.get("/api/scan/bay_f3")
    assert res.status_code == 200
    data = res.json()
    assert data["bay_id"] == "bay_f3"
    assert data["model"] == "Claude Opus 5.5"
    assert len(data["shelf_items"]) > 0
    assert len(data["planogram_items"]) > 0
    assert len(data["action_tasks"]) > 0


def test_scan_invalid_bay():
    res = client.get("/api/scan/bay_invalid_99")
    assert res.status_code == 404
