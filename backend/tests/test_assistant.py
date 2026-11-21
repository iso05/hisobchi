from fastapi.testclient import TestClient

from app.main import create_app


def test_scripted_chat_is_disconnected(tmp_path):
    app = create_app(tmp_path / 'test.sqlite3', 'test-password-123456')
    with TestClient(app) as client:
        for method, path in [('POST', '/api/v1/chat'), ('POST', '/api/v1/assistant/chat'),
                             ('GET', '/api/v1/assistant/status'), ('POST', '/api/v1/assistant/refund')]:
            assert path not in app.openapi()['paths']
            assert client.request(method, path).status_code == 404
