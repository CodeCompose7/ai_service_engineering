"""llm 헬퍼 테스트 — 프로바이더 해석과 호출 카운터.

실제 도구 호출 loop와 생성은 모델이 필요해 예제 실행으로 확인한다.
"""

import pytest

from section3.lec01.llm import call_count, reset_calls, resolve_model


def test_resolve_model_follows_default_provider_ollama():
    env = {
        "DEFAULT_PROVIDER": "ollama",
        "GEMINI_API_KEY": "x",
        "OLLAMA_API_BASE": "http://x",
        "OLLAMA_MODEL": "minimax-m3:cloud",
    }
    model, kwargs = resolve_model(env)
    assert model == "ollama/minimax-m3:cloud"  # 클라우드 키가 있어도 DEFAULT_PROVIDER를 따름
    assert kwargs["api_base"] == "http://x"


def test_resolve_model_follows_default_provider_cloud():
    env = {"DEFAULT_PROVIDER": "openai", "GEMINI_API_KEY": "x", "OPENAI_API_KEY": "y"}
    model, _ = resolve_model(env)
    assert model == "openai/gpt-4o-mini"


def test_resolve_model_falls_back_when_default_absent():
    model, _ = resolve_model({"GEMINI_API_KEY": "x"})  # DEFAULT_PROVIDER 없으면 준비된 첫째
    assert model == "gemini/gemini-2.5-flash"


def test_resolve_model_raises_when_none():
    with pytest.raises(RuntimeError):
        resolve_model({})


def test_call_count_resets_to_zero():
    reset_calls()
    assert call_count() == 0
