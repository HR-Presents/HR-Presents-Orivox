import asyncio
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
