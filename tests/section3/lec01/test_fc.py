"""lec01 fc의 프로바이더 해석 테스트. 실제 도구 호출 loop는 모델이 필요해 예제로 확인한다."""

import pytest

from section3.lec01.fc import resolve_model
from section3.lec01.llm import call_count, reset_calls


def test_call_count_resets_to_zero():
    reset_calls()
    assert call_count() == 0


def test_resolve_model_prefers_cloud_over_ollama():
    env = {
        "DEFAULT_PROVIDER": "ollama",
        "GEMINI_API_KEY": "x",
        "OLLAMA_API_BASE": "http://x",
    }
    model, _ = resolve_model(env)
    assert model == "gemini/gemini-2.5-flash"  # 로컬보다 클라우드 우선


def test_resolve_model_falls_back_to_ollama():
    model, kwargs = resolve_model({"OLLAMA_API_BASE": "http://x", "OLLAMA_MODEL": "gemma4:12b"})
    assert model == "ollama/gemma4:12b"
    assert kwargs["api_base"] == "http://x"


def test_resolve_model_raises_when_none():
    with pytest.raises(RuntimeError):
        resolve_model({})
