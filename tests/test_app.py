import os
from pathlib import Path

os.environ['ORIVOX_DATA_DIR'] = str(Path.cwd() / '.test-data')
os.environ['ORIVOX_DB_PATH'] = str(Path.cwd() / '.test-data' / 'test.db')

from fastapi.testclient import TestClient
from orivox.app import app

client = TestClient(app)


def test_web_client_loads():
    response = client.get('/')
    assert response.status_code == 200
    assert 'ORIVOX' in response.text
    assert 'Your voice.' in response.text
    assert 'Voice Assistant' in response.text
    assert 'brand-symbol' in response.text
    assert 'modelDownloadBanner' in response.text
    assert '<aside class="sidebar">' not in response.text


def test_brand_asset_still_loads_for_release_metadata():
    response = client.get('/brand/orivox-logo.jpg')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/jpeg')
    assert len(response.content) > 1000


def test_status_exposes_dynamic_model_progress_fields():
    response = client.get('/api/status')
    assert response.status_code == 200
    models = response.json()['models']
    assert 'ai_model' in models
    assert 'ai_download_percent' in models
    assert 'ai_download_status' in models


def test_register_login_profile_settings_flow():
    email = 'ci-user@orivox.local'
    reg = client.post('/api/auth/register', json={'name': 'CI User', 'email': email, 'password': 'StrongPass123'})
    assert reg.status_code in (200, 409)
    login = client.post('/api/auth/login', json={'email': email, 'password': 'StrongPass123'})
    assert login.status_code == 200
    user = login.json()
    uid = user['id']
    session = client.get(f'/api/auth/session/{uid}')
    assert session.status_code == 200
    assert session.json()['email'] == email
    profile = client.put(f'/api/profile/{uid}', json={'name': 'CI Updated'})
    assert profile.status_code == 200
    assert profile.json()['name'] == 'CI Updated'
    saved = client.put(f'/api/settings/{uid}', json={'values': {'theme': 'dark', 'voice': 'af_heart', 'speed': '1.1'}})
    assert saved.status_code == 200
    assert saved.json()['theme'] == 'dark'
    settings = client.get(f'/api/settings/{uid}')
    assert settings.status_code == 200
    assert settings.json()['theme'] == 'dark'


def test_empty_transcription_is_rejected():
    response = client.post('/api/transcribe', files={'audio': ('empty.webm', b'', 'audio/webm')})
    assert response.status_code == 400
