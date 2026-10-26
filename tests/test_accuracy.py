"""Accuracy regression cases: geometry, corroboration, matching and API contracts."""
import asyncio
import io
import json

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from server.accuracy import FLASH, OPUS, select_profile
from server.comparison import compare_books, normalize, title_score
from server.recognition import (
    Box, Readings, RecognitionError, VisionClient, load_image, map_box,
    merge_readings, provider_schema, run_recognition, tile_image,
)


@pytest.fixture(autouse=True)
def no_real_credentials(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def image_bytes(size=(100, 50), orientation=None):
    image = Image.new("RGB", size, "white")
    buffer = io.BytesIO()
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def reading(title="Determined", **extra):
    return {"title": title, "author": None, "visible_text": title, "uncertain": False,
            "box": {"top": .2, "left": .1, "width": .3, "height": .4}, **extra}


def response(books, profile=OPUS, complete=True, **overrides):
    if profile == OPUS:
        payload = {"model": profile.model_id, "stop_reason": "end_turn" if complete else "max_tokens", "content": [{"type": "text", "text": json.dumps({"books": books})}], "usage": {"input_tokens": 100, "output_tokens": 20}}
    else:
        payload = {"modelVersion": profile.model_id, "candidates": [{"finishReason": "STOP" if complete else "MAX_TOKENS", "content": {"parts": [{"text": json.dumps({"books": books})}]}}], "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 7}}
    return httpx.Response(200, json={**payload, **overrides})


@pytest.mark.parametrize("difficulty,expected", [("easy", FLASH), ("medium", OPUS), ("hard", OPUS)])
def test_report_policy_by_difficulty(difficulty, expected):
    assert select_profile(difficulty) == expected


def test_live_capabilities_and_explicit_fallback(monkeypatch):
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        select_profile("hard", live=True)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert select_profile("easy", live=True) == FLASH
    with pytest.raises(ValueError):
        select_profile("hard", live=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY")
    selected = select_profile("easy", live=True)
    assert selected.model_id == OPUS.model_id
    assert "unavailable" in selected.reason
    assert select_profile("easy", "opus", live=True) == OPUS


@pytest.mark.parametrize("size", [(100, 90), (1400, 1400), (1401, 1401), (1300, 956), (1080, 1440), (4284, 5712), (5712, 4284)])
def test_tiles_cover_entire_original_without_downscaling(size):
    tiles = tile_image(size)
    assert len({t.bounds for t in tiles}) == len(tiles)
    width, height = size
    # For every horizontal band, the tile intervals must cover the whole width.
    ys = sorted({0, height, *(t.bounds[1] for t in tiles), *(t.bounds[3] for t in tiles)})
    for top, bottom in zip(ys, ys[1:]):
        intervals = sorted((t.bounds[0], t.bounds[2]) for t in tiles if t.bounds[1] <= top and t.bounds[3] >= bottom)
        reached = 0
        for left, right in intervals:
            assert left <= reached
            reached = max(reached, right)
        assert reached == width
    for t in tiles:
        left, top, right, bottom = t.bounds
        assert 0 < right-left <= 1400 and 0 < bottom-top <= 1400
        assert 0 <= left < right <= width and 0 <= top < bottom <= height


def test_oversized_grid_fails_instead_of_skipping_regions():
    with pytest.raises(RecognitionError, match="smaller sections"):
        tile_image((10000, 10000))


@pytest.mark.parametrize("orientation,size", [(1, (100, 50)), (6, (50, 100)), (8, (50, 100))])
def test_exif_orientation_matches_browser_frame(orientation, size):
    assert load_image(image_bytes(orientation=orientation)).size == size


def test_invalid_image_rejected():
    with pytest.raises(RecognitionError, match="decoded"):
        load_image(b"not an image")


def test_rotated_boxes_map_back_to_same_native_location():
    original = {"top": .2, "left": .1, "width": .3, "height": .4}
    rotated = {"top": .1, "left": .4, "width": .4, "height": .3}
    bounds = (1120, 2240, 2520, 3640)
    normal = map_box(original, bounds, (4284, 5712))
    inverse = map_box(rotated, bounds, (4284, 5712), rotated=True)
    assert inverse == pytest.approx(normal)
    assert normal["left"] == pytest.approx(1260/4284)


@pytest.mark.parametrize("box", [
    {"top": -.1, "left": 0, "width": .1, "height": .1},
    {"top": 0, "left": .9, "width": .2, "height": .1},
    {"top": 0, "left": 0, "width": 0, "height": .1},
    {"top": 0, "left": 0, "width": float("nan"), "height": .1},
    {"top": 0, "left": 0, "width": float("inf"), "height": .1},
])
def test_invalid_geometry_never_becomes_an_outline(box):
    with pytest.raises(ValidationError):
        Box.model_validate(box)


def obs(phase="read", title="Determined", **kwargs):
    return {**reading(title), "pass": phase, "tile_id": "tile-1", **kwargs}


def test_overlapping_repeats_do_not_become_extra_titles():
    merged = merge_readings([obs(), obs(tile_id="tile-2"), obs("verify")])
    assert len(merged) == 1
    assert merged[0]["verification_status"] == "verified"
    assert merged[0]["confidence"] is None
    assert len(merged[0]["evidence"]) == 3


def test_same_pass_or_different_location_cannot_corroborate():
    assert merge_readings([obs(), obs(tile_id="tile-2")])[0]["verification_status"] == "needs_review"
    other = obs("verify", box={"top": .8, "left": .8, "width": .1, "height": .1})
    assert merge_readings([obs(), other])[0]["verification_status"] == "needs_review"


def test_conflicting_titles_or_uncertainty_remain_review_items():
    merged = merge_readings([obs(), obs("verify"), obs("verify", title="Behave")])
    assert all(b["verification_status"] == "needs_review" for b in merged)
    assert merge_readings([obs(), obs("verify", uncertain=True)])[0]["verification_status"] == "needs_review"


def test_conflicting_authors_stay_unknown():
    result = merge_readings([obs(author="A"), obs("verify", author="B")])[0]
    assert result["author"] is None


def test_title_normalization_preserves_non_latin_marks_and_numbers():
    assert normalize("Café & Art") == "cafe and art"
    assert normalize("जादू") == "जादू"
    assert normalize("जादू") != normalize("जद")
    assert title_score("The Trial", "Trial") == 1
    assert title_score("Attack on Titan: Volume 1", "Attack on Titan: Volume 2") == 0
    assert title_score("Harry Potter", "Harry Potter and the Goblet of Fire") == 0
    assert title_score("You Can", "You Can Win") == 0
    assert title_score("Diary of a Wimpy Kid", "Diary of a Wimpy Kid: The Long Haul") == 0
    assert title_score("Racine: Modern Judgements", "Modern Judgements: Racine") >= .85


def tiny_store():
    def item(sku, title, bay="bay_a1", on_hand=2):
        return {"sku": sku, "title": title, "author": None, "assigned_bay_id": bay, "price": 10, "simulated_on_hand": on_hand, "sales_velocity_units_per_day": 1}
    bay = {"id": "bay_a1", "name": "Shelf A"}
    store = {"bays": [bay, {"id": "bay_b1", "name": "Shelf B"}], "catalogue": {
        "a": item("a", "Determined"), "b": item("b", "Behave", on_hand=0),
        "c": item("c", "Deep Work", bay="bay_b1"),
    }}
    return store, bay


def test_unrecognized_books_are_not_asserted_stockouts():
    store, bay = tiny_store()
    result = compare_books(store, bay, [])
    assert result["metrics"]["planogram_compliance_pct"] == 0
    assert all(not m["is_phantom_inventory"] for m in result["missing_items"])
    assert all(t["requires_review"] for t in result["action_tasks"])
    assert all("shelf_count" not in t for t in result["action_tasks"])


def test_comparison_uses_inventory_instead_of_planted_answers():
    store, bay = tiny_store()
    result = compare_books(store, bay, [reading("Behave"), reading("Deep Work")])
    assert result["metrics"]["matched_count"] == 1
    assert result["misplaced_items"][0]["target_bay_name"] == "Shelf B"
    assert {t["type"] for t in result["action_tasks"]} == {"record_error", "misplaced_item", "missing_item"}
    assert result["metrics"]["planogram_compliance_pct"] <= 100


def test_uncorroborated_read_cannot_satisfy_planogram_or_trigger_record_correction():
    store, bay = tiny_store()
    result = compare_books(store, bay, [reading("Behave", verification_status="needs_review")])
    assert result["metrics"]["matched_count"] == 0
    assert not any(t["type"] == "record_error" for t in result["action_tasks"])
    assert any(t["type"] == "recognition_review" for t in result["action_tasks"])


def test_catalogue_matching_is_one_to_one_and_does_not_invent_authors():
    store, bay = tiny_store()
    store["catalogue"]["a"]["author"] = "Robert Sapolsky"
    result = compare_books(store, bay, [reading(), reading()])
    assert result["metrics"]["matched_count"] == 1
    assert result["shelf_items"][0]["author"] is None
    assert result["shelf_items"][1]["status"] == "needs_review"


def test_same_book_allocated_to_two_bays_prefers_valid_local_allocation():
    store, bay = tiny_store()
    store["catalogue"]["d"] = {**store["catalogue"]["a"], "sku": "d", "assigned_bay_id": "bay_b1"}
    result = compare_books(store, bay, [reading()])
    assert result["shelf_items"][0]["status"] == "matched"
    assert result["shelf_items"][0]["sku"] == "a"
    assert result["metrics"]["matched_count"] == 1


def test_same_title_by_different_authors_is_ambiguous_without_visible_author():
    store, bay = tiny_store()
    store["catalogue"]["a"]["author"] = "Robert Sapolsky"
    store["catalogue"]["d"] = {**store["catalogue"]["a"], "sku": "d", "author": "Someone Else", "assigned_bay_id": "bay_b1"}
    result = compare_books(store, bay, [reading()])
    assert result["shelf_items"][0]["status"] == "needs_review"


def test_api_schema_compatible_but_local_validation_strict():
    schema = provider_schema()
    encoded = json.dumps(schema)
    for key in ("minimum", "maximum", "minLength", "maxLength", "maxItems", "exclusiveMinimum"):
        assert f'"{key}"' not in encoded
    assert schema["additionalProperties"] is False
    with pytest.raises(ValidationError):
        Readings.model_validate({"books": [reading(visible_text=" ")]})
    with pytest.raises(ValidationError):
        Readings.model_validate({"books": [reading(visible_text="...")]})
    assert Readings.model_validate({"books": [reading(author="???")]}).books[0].author is None
    assert Readings.model_validate({"books": [reading(visible_text="Robert Sapolsky")]}).books[0].uncertain


@pytest.mark.parametrize("profile", [OPUS, FLASH])
def test_provider_payload_enforces_high_settings_and_validates_identity(monkeypatch, profile):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    seen = []
    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        if profile == OPUS:
            assert body["model"] == "claude-opus-5-5"
            assert body["thinking"] == {"type": "adaptive"}
            assert body["output_config"]["effort"] == "high"
            assert len(body["messages"][0]["content"]) == 2
            assert request.headers["x-api-key"] == "test-only-key"
        else:
            config = body["generationConfig"]
            assert config["thinkingConfig"] == {"thinkingLevel": "HIGH"}
            assert config["mediaResolution"] == "MEDIA_RESOLUTION_HIGH"
            assert config["responseMimeType"] == "application/json"
            assert len(body["contents"][0]["parts"]) == 2
            assert request.headers["x-goog-api-key"] == "test-only-key"
        return response([reading()], profile)
    client = VisionClient(profile, httpx.MockTransport(handler))
    books = asyncio.run(client.read(Image.new("RGB", (10, 10)), "read", "tile-1"))
    assert len(books) == 1 and len(seen) == 1
    assert client.calls[0]["actual_model"] == profile.model_id


@pytest.mark.parametrize("failure", ["truncated", "model_substitution", "invalid_json", "invalid_box"])
def test_invalid_responses_fail_instead_of_using_partial_output(monkeypatch, failure):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    def handler(request):
        if failure == "truncated":
            return response([reading()], complete=False)
        if failure == "model_substitution":
            return response([reading()], model="claude-sonnet-5-5")
        if failure == "invalid_json":
            return response([], content=[{"type": "text", "text": '{"books": ['}])
        return response([reading(box={"top": .9, "left": .9, "width": .5, "height": .5})])
    client = VisionClient(OPUS, httpx.MockTransport(handler))
    with pytest.raises(RecognitionError):
        asyncio.run(client.read(Image.new("RGB", (10, 10)), "read", "tile-1"))


def test_bad_credentials_are_not_retried_and_never_echo_secrets(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-test-key")
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(401, text="private-test-key and sensitive response body")
    client = VisionClient(OPUS, httpx.MockTransport(handler))
    with pytest.raises(RecognitionError) as exc:
        asyncio.run(client.read(Image.new("RGB", (10, 10)), "read", "tile-1"))
    assert len(requests) == 1
    assert "private-test-key" not in str(exc.value)


def test_transient_failure_has_bounded_retry(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    async def no_wait(seconds):
        pass
    monkeypatch.setattr("server.recognition.asyncio.sleep", no_wait)
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(429) if len(requests) < 3 else response([])
    client = VisionClient(OPUS, httpx.MockTransport(handler))
    assert asyncio.run(client.read(Image.new("RGB", (10, 10)), "read", "tile-1")) == []
    assert len(requests) == 3


def test_complete_harness_reads_verifies_maps_and_audits(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-test-key")
    monkeypatch.setattr("server.recognition.RUNS_DIR", tmp_path)
    requests, events = [], []
    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return response([reading()])
        # The independent request has no candidate titles from the first pass.
        text = body["messages"][0]["content"][1]["text"]
        assert "Determined" not in text
        return response([reading(box={"top": .1, "left": .4, "width": .4, "height": .3})])
    async def emit(event):
        events.append(event)
    books, metadata = asyncio.run(run_recognition(image_bytes(), OPUS, emit, transport=httpx.MockTransport(handler)))
    assert len(requests) == 2
    assert books[0]["verification_status"] == "verified"
    assert books[0]["box"] == pytest.approx(reading()["box"])
    assert metadata["mode"] == "live"
    assert metadata["tokens_used"] == 240
    assert metadata["harness"]["calls_completed"] == 2
    assert metadata["harness"]["measured_accuracy"] is None
    audit_text = (tmp_path / f"{metadata['run_id']}.json").read_text()
    audit = json.loads(audit_text)
    assert audit["status"] == "complete"
    assert "private-test-key" not in audit_text
    assert "base64" not in audit_text
    assert audit["calls"][0]["actual_model"] == OPUS.model_id
    assert [e["status"] for e in events] == ["preparing", "reading", "verifying"]


def test_failure_is_audited_and_never_returns_replay(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-key")
    monkeypatch.setattr("server.recognition.RUNS_DIR", tmp_path)
    async def emit(event):
        pass
    with pytest.raises(RecognitionError):
        asyncio.run(run_recognition(image_bytes(), OPUS, emit, transport=httpx.MockTransport(lambda request: httpx.Response(403))))
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["status"] == "failed_or_cancelled"
