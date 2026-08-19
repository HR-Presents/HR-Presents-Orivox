import asyncio
import os
import httpx

from orivox.services import Runtime


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, timeout=None):
        self.__class__.calls.append((url, json, timeout))
        request = httpx.Request('POST', url)
        chat_calls = [c for c in self.__class__.calls if c[0].endswith('/api/chat')]
        if url.endswith('/api/chat') and len(chat_calls) == 1:
            return httpx.Response(404, json={'error': "model 'qwen2.5:3b' not found"}, request=request)
        if url.endswith('/api/pull'):
            return httpx.Response(200, json={'status': 'success'}, request=request)
        if url.endswith('/api/chat'):
            return httpx.Response(200, json={'message': {'content': 'hello from local model'}}, request=request)
        raise AssertionError(f'unexpected URL {url}')


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeWhisperModel:
    def __init__(self):
        self.seen_path = None
        self.seen_bytes = None

    def transcribe(self, path, vad_filter=True):
        self.seen_path = path
        with open(path, 'rb') as f:
            self.seen_bytes = f.read()
        assert vad_filter is True
        return [FakeSegment('hello'), FakeSegment('world')], None


def test_chat_auto_pulls_missing_model(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr('orivox.services.httpx.AsyncClient', FakeAsyncClient)
    runtime = Runtime()

    text = asyncio.run(runtime.chat([{'role': 'user', 'content': 'hello'}], model='qwen2.5:3b'))

    assert text == 'hello from local model'
    urls = [call[0] for call in FakeAsyncClient.calls]
    assert urls == [
        'http://127.0.0.1:11434/api/chat',
        'http://127.0.0.1:11434/api/pull',
        'http://127.0.0.1:11434/api/chat',
    ]
    assert runtime.status['ai'] == 'ready'


def test_transcribe_browser_webm_uses_temp_file(monkeypatch):
    runtime = Runtime()
    model = FakeWhisperModel()
    monkeypatch.setattr(runtime, 'load_whisper', lambda: model)
    webm = b'\x1a\x45\xdf\xa3' + b'fake-webm-payload'

    text = asyncio.run(runtime.transcribe(webm))

    assert text == 'hello world'
    assert model.seen_bytes == webm
    assert model.seen_path.endswith('.webm')
    assert not os.path.exists(model.seen_path)
