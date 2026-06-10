"""S5 lec01 FastAPI 서빙 테스트.

엔드포인트·입력 검증·에러 처리·스트리밍을 모델 없이 본다. resolve_model과 모델 호출을 가짜로
갈아끼워, 실제 LLM 없이 결정적으로 확인한다.
"""

import pytest
from fastapi.testclient import TestClient

import section5.lec01.server as server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "resolve_model", lambda: ("fake/model", {}))
    with TestClient(server.app) as c:
        yield c


def test_validation_rejects_empty(client):
    resp = client.post("/generate", json={"question": ""})
    assert resp.status_code == 422  # 빈 질문은 핸들러에 닿기 전에 막힌다


def test_generate_returns_answer(client, monkeypatch):
    async def fake_completion(model, messages, kwargs):
        return "가짜 답"

    monkeypatch.setattr(server, "run_completion", fake_completion)
    resp = client.post("/generate", json={"question": "안녕?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": "가짜 답"}


def test_generate_handles_model_error(client, monkeypatch):
    async def boom(model, messages, kwargs):
        raise RuntimeError("연결 끊김")

    monkeypatch.setattr(server, "run_completion", boom)
    resp = client.post("/generate", json={"question": "안녕?"})
    assert resp.status_code == 502  # 모델 실패는 502로 또렷이


def test_stream_concatenates_tokens(client, monkeypatch):
    async def fake_stream(model, messages, kwargs):
        for token in ["안", "녕", "!"]:
            yield token

    monkeypatch.setattr(server, "run_stream", fake_stream)
    with client.stream("POST", "/generate/stream", json={"question": "인사해"}) as s:
        body = "".join(s.iter_text())
    assert body == "안녕!"
