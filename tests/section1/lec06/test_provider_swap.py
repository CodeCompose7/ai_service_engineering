"""lec06 provider_swap의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(프로바이더 탐지·모델 문자열·호출 인자)만 검증한다.
"""

from section1.lec06.provider_swap import (
    DEFAULT_MODEL,
    api_base_kwargs,
    available_providers,
    model_for,
    provider_models,
)


def test_available_providers_detects_filled_keys_and_ollama():
    env = {
        "GEMINI_API_KEY": "x",
        "OPENAI_API_KEY": "y",
        "ANTHROPIC_API_KEY": "",  # 빈 값은 준비 안 된 것으로 본다
        "OLLAMA_API_BASE": "http://h:11434",
    }
    assert available_providers(env) == ["gemini", "openai", "ollama"]


def test_available_providers_empty_env():
    assert available_providers({}) == []


def test_model_for_each_cloud_provider():
    assert model_for("gemini", {}) == "gemini/gemini-2.5-flash"
    assert model_for("openai", {}) == "openai/gpt-4o-mini"
    assert model_for("anthropic", {}) == "anthropic/claude-haiku-4-5"


def test_model_for_ollama_uses_env_model():
    assert model_for("ollama", {"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_api_base_kwargs_ollama_uses_base():
    assert api_base_kwargs("ollama", {"OLLAMA_API_BASE": "http://h:11434"}) == {
        "api_base": "http://h:11434"
    }


def test_api_base_kwargs_cloud_is_empty():
    assert api_base_kwargs("gemini", {}) == {}


def test_provider_models_pairs_each_provider_with_model_string():
    env = {"OLLAMA_MODEL": "gemma4:12b"}
    pairs = provider_models(["gemini", "ollama"], env)
    assert pairs == [
        ("gemini", "gemini/gemini-2.5-flash"),
        ("ollama", "ollama/gemma4:12b"),
    ]


def test_default_model_is_a_provider_prefixed_string():
    assert DEFAULT_MODEL.startswith("gemini/")
