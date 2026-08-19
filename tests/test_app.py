import os
from pathlib import Path
os.environ['ORIVOX_DATA_DIR']=str(Path.cwd()/'.test-data')
os.environ['ORIVOX_DB_PATH']=str(Path.cwd()/'.test-data'/'test.db')
from fastapi.testclient import TestClient
from orivox.app import app

client=TestClient(app)

def test_web_client_loads():
    r=client.get('/')
    assert r.status_code==200
    assert 'ORIVOX' in r.text

def test_register_login_profile_settings_flow():
    email='ci-user@orivox.local'
    reg=client.post('/api/auth/register',json={'name':'CI User','email':email,'password':'StrongPass123'})
    assert reg.status_code in (200,409)
    login=client.post('/api/auth/login',json={'email':email,'password':'StrongPass123'})
    assert login.status_code==200
    user=login.json(); uid=user['id']
    profile=client.put(f'/api/profile/{uid}',json={'name':'CI Updated'})
    assert profile.status_code==200
    assert profile.json()['name']=='CI Updated'
    saved=client.put(f'/api/settings/{uid}',json={'values':{'theme':'dark','voice':'af_heart','speed':'1.1'}})
    assert saved.status_code==200
    settings=client.get(f'/api/settings/{uid}')
    assert settings.status_code==200
    assert settings.json()['theme']=='dark'

def test_empty_transcription_is_rejected():
    r=client.post('/api/transcribe',files={'audio':('empty.webm',b'','audio/webm')})
    assert r.status_code==400
