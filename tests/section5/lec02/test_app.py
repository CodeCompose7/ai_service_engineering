"""S5 lec02 통합 웹 서비스 테스트.

채팅·관찰·설정 엔드포인트와 페이지 서빙을 모델·인덱스 없이 본다. LLM 의존을 가짜로 갈아끼우고
인덱스 로딩을 건너뛴다.
"""

import pytest
from fastapi.testclient import TestClient

import section5.lec02.app as appmod
import section5.lec02.assistant as assistant


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(appmod, "open_index", lambda: None)

    async def no(_message):
        return False

    async def fake_complete(_messages):
        return "테스트 답"

    monkeypatch.setattr(assistant, "detect_injection", no)
    monkeypatch.setattr(assistant, "llm_moderate", no)
    monkeypatch.setattr(assistant, "acomplete", fake_complete)
    with TestClient(appmod.app) as c:
        yield c


def test_chat_returns_answer(client):
    resp = client.post("/chat", json={"message": "안녕?", "user": "alice"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "테스트 답"


def test_chat_validation_rejects_empty(client):
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_metrics_after_chat(client):
    client.post("/chat", json={"message": "안녕?", "user": "alice"})
    data = client.get("/api/metrics").json()
    assert data["overall"]["requests"] == 1
    assert "alice" in data["by_user"]


def test_settings_toggle(client):
    assert client.post("/api/settings", json={"rag": False}).json()["rag"] is False


def test_pages_serve(client):
    home = client.get("/")
    assert home.status_code == 200
    assert "통합 어시스턴트" in home.text
    assert client.get("/admin").status_code == 200


def test_chat_stream(client, monkeypatch):
    async def fake_stream(_messages):
        for token in ["테", "스", "트"]:
            yield token

    monkeypatch.setattr(assistant, "_generate_stream", fake_stream)
    with client.stream("POST", "/chat/stream", json={"message": "안녕?", "user": "web"}) as s:
        body = "".join(s.iter_text())
    assert body == "테스트"
