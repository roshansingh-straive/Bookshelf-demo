"""test_server.py: Tests for FastAPI backend server."""
import json
from fastapi.testclient import TestClient
from server.main import app
from server.recognition import RecognitionError

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


def parse_events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_replay_stream_does_not_claim_live_model_or_verification():
    res = client.post("/api/scan/stream", json={"bay_id": "bay_a1", "mode": "replay"})
    assert res.status_code == 200
    events = parse_events(res)
    assert [e["status"] for e in events] == ["replay", "complete"]
    assert events[-1]["result"]["mode"] == "replay"
    assert events[-1]["result"]["model"] == "Gemini 3.8 Flash"
    assert not events[-1]["result"]["harness"]["rotated_verification"]


def test_live_without_credentials_fails_explicitly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = client.post("/api/scan/stream", json={"bay_id": "bay_f3", "mode": "live"})
    assert res.status_code == 503
    assert "ANTHROPIC_API_KEY" in res.json()["detail"]
    health = client.get("/api/health").json()
    assert not health["live_mode_available"]
    assert not any(health["live_available_by_difficulty"].values())


def test_other_credentials_do_not_falsely_enable_live_scans(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("LLM_PROXY_TOKEN", "test-only")
    assert not client.get("/api/health").json()["live_mode_available"]


def test_scan_request_rejects_unknown_modes_models_and_paths():
    for payload in (
        {"bay_id": "../store", "mode": "replay"},
        {"bay_id": "bay_f3", "mode": "fake"},
        {"bay_id": "bay_f3", "model_id": "unmeasured-model"},
        {"bay_id": "bay_f3", "custom_image_b64": "different photo"},
    ):
        assert client.post("/api/scan/stream", json=payload).status_code == 422


def test_live_stream_runs_recognition_and_compares_actual_output(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.setattr("server.main.PHOTOS_DIR", tmp_path)
    (tmp_path / "f.jpg").write_bytes(b"test photo supplied to mocked recognition")
    calls = []
    async def recognize(raw, profile, emit):
        calls.append((raw, profile))
        await emit({"step": 1, "status": "reading", "message": "real work"})
        return [], {"mode": "live", "model": profile.name, "effort": "high"}
    monkeypatch.setattr("server.main.run_recognition", recognize)
    events = parse_events(client.post("/api/scan/stream", json={"bay_id": "bay_f3", "mode": "live"}))
    assert [e["status"] for e in events] == ["reading", "comparing", "complete"]
    result = events[-1]["result"]
    assert result["mode"] == "live"
    assert result["shelf_items"] == []
    assert result["metrics"]["matched_count"] == 0
    assert len(calls) == 1
    assert calls[0][1].model_id == "claude-opus-5-5"


def test_streamed_failure_does_not_substitute_replay(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    async def fail(raw, profile, emit):
        raise RecognitionError("Provider unavailable")
    monkeypatch.setattr("server.main.run_recognition", fail)
    events = parse_events(client.post("/api/scan/stream", json={"bay_id": "bay_f3", "mode": "live"}))
    assert events == [{"status": "error", "message": "Provider unavailable"}]


def test_server_will_not_start_multiple_paid_scans(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    class BusyLock:
        def locked(self):
            return True
    monkeypatch.setattr("server.main._live_scan_lock", BusyLock())
    res = client.post("/api/scan/stream", json={"bay_id": "bay_f3", "mode": "live"})
    assert res.status_code == 409


def test_unknown_api_route_does_not_return_the_frontend():
    assert client.get("/api/nonexistent-route").status_code == 404
