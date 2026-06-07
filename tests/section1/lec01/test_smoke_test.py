"""lec01 smoke_test의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(프로바이더 탐지·시도 순서·모델 문자열)만 검증한다.
"""

from section1.lec01.smoke_test import (
    available_providers,
    model_and_kwargs,
    provider_order,
)


def test_available_providers_detects_filled_keys_only():
    env = {
        "GEMINI_API_KEY": "x",
        "OPENAI_API_KEY": "",  # 빈 값은 준비 안 된 것으로 본다
        "OLLAMA_API_BASE": "http://host.docker.internal:11434",
    }
    assert available_providers(env) == ["gemini", "ollama"]


def test_available_providers_empty_env():
    assert available_providers({}) == []


def test_provider_order_puts_default_first():
    assert provider_order("ollama", ["gemini", "ollama"]) == ["ollama", "gemini"]


def test_provider_order_ignores_unavailable_default():
    # default가 준비 안 됐으면 무시하고 available 순서를 따른다
    assert provider_order("openai", ["gemini", "ollama"]) == ["gemini", "ollama"]


def test_provider_order_without_default():
    assert provider_order(None, ["gemini", "ollama"]) == ["gemini", "ollama"]


def test_model_and_kwargs_ollama_uses_base_and_model():
    env = {"OLLAMA_MODEL": "gemma4:12b", "OLLAMA_API_BASE": "http://host.docker.internal:11434"}
    model, kwargs = model_and_kwargs("ollama", env)
    assert model == "ollama/gemma4:12b"
    assert kwargs == {"api_base": "http://host.docker.internal:11434"}


def test_model_and_kwargs_cloud_has_no_extra_kwargs():
    model, kwargs = model_and_kwargs("gemini", {})
    assert model.startswith("gemini/")
    assert kwargs == {}
