import pytest
from fastapi.testclient import TestClient

from app import lexai
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / 'test.sqlite3', 'test-password-123456')) as api:
        yield api


def test_live_contract(client, monkeypatch):
    seen = {}
    expected = {'answer': 'Model answer', 'verified': False, 'latency_ms': 7,
                'sources': [{'id': 'A1', 'reference': 'Article 1', 'text': 'Excerpt'}]}

    class Remote:
        def __init__(self, url, **options):
            seen['url'] = url

        def submit(self, **kwargs):
            seen.update(kwargs)
            return self

        def result(self, timeout):
            return expected

        def close(self):
            seen['closed'] = True

    monkeypatch.setenv('LEXAI_URL', 'https://example.test')
    monkeypatch.setattr(lexai, 'Client', Remote)
    response = client.post('/api/v1/assistant/chat', json={'question': '  Test?  '})
    assert response.json() == expected
    assert seen == {'url': 'https://example.test', 'api_name': '/ask_json', 'question': 'Test?', 'closed': True}


def test_chat_error_paths(client, monkeypatch):
    path = '/api/v1/assistant/chat'
    monkeypatch.delenv('LEXAI_URL', raising=False)
    assert client.post(path, json={'question': 'Hi'}).status_code == 503
    for question in (' ', 'a' * 3001):
        assert client.post(path, json={'question': question}).status_code == 422
    assert client.post(path, json={'question': 'Hi'}, headers={'Origin': 'https://example.invalid'}).status_code == 403
    assert client.post('/api/v1/assistant/refund').status_code == 404
