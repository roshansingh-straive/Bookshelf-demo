"""Uploaded photos must remain distinct from saved benchmark/sample results."""
import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server.main import app
from server.recognition import RecognitionError

client = TestClient(app)


@pytest.fixture(autouse=True)
def local_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr('server.uploads.UPLOADS_DIR', tmp_path)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    return tmp_path


def picture(format='PNG', orientation=None):
    image = Image.new('RGB', (80, 40), '#b2c6ef')
    buffer = io.BytesIO()
    options = {}
    if orientation:
        exif = Image.Exif()
        exif[274] = orientation
        options['exif'] = exif
    image.save(buffer, format=format, **options)
    return buffer.getvalue()


def upload(raw=None, name='my-shelf.png'):
    return client.post('/api/uploads', params={'filename': name}, content=raw or picture(), headers={'Content-Type': 'application/octet-stream'})


@pytest.mark.parametrize('format', ['JPEG', 'PNG', 'WEBP'])
def test_valid_upload_returns_its_actual_photo_and_metadata(format):
    raw = picture(format)
    response = upload(raw, f'shelf.{format.lower()}')
    assert response.status_code == 201
    photo = response.json()
    assert len(photo['upload_id']) == 32
    assert (photo['width'], photo['height']) == (80, 40)
    assert photo['byte_size'] == len(raw)
    served = client.get(photo['photo_url'])
    assert served.status_code == 200
    assert served.content == raw
    assert served.headers['content-type'] == photo['media_type']
    assert served.headers['x-content-type-options'] == 'nosniff'
    assert client.get(f"/api/uploads/{photo['upload_id']}").json() == photo


def test_uploaded_exif_dimensions_match_the_browser():
    response = upload(picture('JPEG', orientation=6), 'portrait.jpg')
    assert response.status_code == 201
    assert (response.json()['width'], response.json()['height']) == (40, 80)


def test_filenames_cannot_control_storage_paths(local_uploads):
    photo = upload(name='../nested\\my-shelf.png\r\n').json()
    assert photo['filename'] == 'my-shelf.png'
    assert (local_uploads / photo['upload_id'] / 'image').is_file()
    assert len(list(local_uploads.iterdir())) == 1


@pytest.mark.parametrize('raw', [b'not an image', b'<svg><script>bad()</script></svg>', picture('GIF')])
def test_image_bytes_are_validated_instead_of_trusting_the_filename(raw, local_uploads):
    response = upload(raw, 'fake-photo.png')
    assert response.status_code == 422
    assert not list(local_uploads.iterdir())


def test_upload_size_limit_is_enforced_before_saving(monkeypatch, local_uploads):
    monkeypatch.setattr('server.main.MAX_IMAGE_BYTES', 8)
    response = upload(b'123456789')
    assert response.status_code == 413
    assert not list(local_uploads.iterdir())


def test_unknown_photo_and_invalid_ids_are_not_replayed():
    for path in ['/api/uploads/not-a-valid-id', f"/api/uploads/{'a'*32}/image", f"/api/uploads/{'a'*32}/analysis/bay_f3"]:
        assert client.get(path).status_code == 404


def test_upload_cannot_use_a_saved_sample_result():
    photo = upload().json()
    response = client.post('/api/scan/stream', json={'bay_id': 'bay_f3', 'upload_id': photo['upload_id'], 'mode': 'replay'})
    assert response.status_code == 422
    assert 'Sample results cannot be used' in response.json()['detail']
    assert client.get(f"/api/uploads/{photo['upload_id']}/analysis/bay_f3").json() == {'result': None}


def test_unavailable_live_service_keeps_upload_without_claiming_results():
    photo = upload().json()
    response = client.post('/api/scan/stream', json={'bay_id': 'bay_f3', 'upload_id': photo['upload_id'], 'mode': 'live'})
    assert response.status_code == 401
    assert client.get(photo['photo_url']).status_code == 200
    assert client.get(f"/api/uploads/{photo['upload_id']}/analysis/bay_f3").json() == {'result': None}
    assert client.get('/api/health').json()['upload_analysis_available']


def test_personal_provider_key_does_not_replace_foundry_session(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    photo = upload().json()
    response = client.post('/api/scan/stream', json={'bay_id': 'bay_a1', 'upload_id': photo['upload_id'], 'mode': 'live'})
    assert response.status_code == 401
    health = client.get('/api/health').json()
    assert health['live_available_by_difficulty']['easy']
    assert health['upload_analysis_available']


def test_analysis_reads_uploaded_bytes_and_persists_result_for_refresh(monkeypatch):
    raw = picture()
    photo = upload(raw, 'actual-upload.png').json()
    calls = []
    async def recognize(image, profile, emit, token):
        calls.append((image, profile, token))
        await emit({'step': 1, 'status': 'reading'})
        return [], {'mode': 'live', 'model': profile.name, 'effort': 'high', 'run_id': 'test-run'}
    monkeypatch.setattr('server.main.run_recognition', recognize)
    token = 'ephemeral-test-token'
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post('/api/scan/stream', json={'bay_id': 'bay_a1', 'upload_id': photo['upload_id'], 'mode': 'live'}, headers=headers)
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert [event['status'] for event in events] == ['reading', 'comparing', 'complete']
    result = events[-1]['result']
    assert calls[0][0] == raw
    assert calls[0][1].model_id == 'gemini-3.1-pro-preview'
    assert calls[0][2] == token
    assert result['upload_id'] == photo['upload_id']
    assert result['source_kind'] == 'upload'
    assert result['photo_url'] == photo['photo_url']
    assert result['photo_filename'] == 'actual-upload.png'
    assert result['shelf_items'] == []
    assert result['metrics']['matched_count'] == 0
    assert token not in json.dumps(result)
    assert client.get(f"/api/uploads/{photo['upload_id']}/analysis/bay_a1").json()['result'] == result
    assert client.get(f"/api/uploads/{photo['upload_id']}/analysis/bay_f3").json()['result'] is None
    # A later failed rescan must leave the completed analysis intact.
    async def fail(*args):
        raise RecognitionError('Provider unavailable')
    monkeypatch.setattr('server.main.run_recognition', fail)
    failed = client.post('/api/scan/stream', json={'bay_id': 'bay_a1', 'upload_id': photo['upload_id'], 'mode': 'live'}, headers=headers)
    assert '"status": "error"' in failed.text
    assert client.get(f"/api/uploads/{photo['upload_id']}/analysis/bay_a1").json()['result'] == result
