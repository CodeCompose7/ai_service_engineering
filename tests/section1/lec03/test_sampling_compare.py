"""lec03 sampling_compare의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(프로바이더 탐지·파라미터 보정·모델 문자열)만 검증한다.
"""

from section1.lec03.sampling_compare import (
    available_providers,
    demo_provider,
    max_temperature,
    model_for,
    provider_order,
    safe_sampling_kwargs,
    supports_top_k,
)


def test_supports_top_k_openai_false_others_true():
    assert supports_top_k("openai") is False
    assert supports_top_k("gemini") is True
    assert supports_top_k("anthropic") is True
    assert supports_top_k("ollama") is True


def test_max_temperature_anthropic_capped_others_default():
    assert max_temperature("anthropic") == 1.0
    assert max_temperature("openai") == 2.0
    assert max_temperature("gemini") == 2.0


def test_safe_sampling_drops_top_k_for_openai():
    kwargs = safe_sampling_kwargs("openai", temperature=0.5, top_p=0.9, top_k=40)
    assert "top_k" not in kwargs
    assert kwargs["temperature"] == 0.5
    assert kwargs["top_p"] == 0.9


def test_safe_sampling_keeps_top_k_for_supported_provider():
    kwargs = safe_sampling_kwargs("gemini", top_k=40)
    assert kwargs == {"top_k": 40}


def test_safe_sampling_clamps_temperature_for_anthropic():
    # 1.8을 줘도 Anthropic 상한 1.0으로 잘린다
    kwargs = safe_sampling_kwargs("anthropic", temperature=1.8)
    assert kwargs["temperature"] == 1.0


def test_safe_sampling_does_not_clamp_within_range():
    kwargs = safe_sampling_kwargs("openai", temperature=1.5)
    assert kwargs["temperature"] == 1.5


def test_safe_sampling_omits_unset_params():
    assert safe_sampling_kwargs("gemini") == {}


def test_available_providers_detects_filled_keys_only():
    env = {
        "OPENAI_API_KEY": "x",
        "GEMINI_API_KEY": "",  # 빈 값은 준비 안 된 것으로 본다
        "OLLAMA_API_BASE": "http://host.docker.internal:11434",
    }
    assert available_providers(env) == ["openai", "ollama"]


def test_provider_order_puts_default_first():
    assert provider_order("ollama", ["gemini", "ollama"]) == ["ollama", "gemini"]


def test_model_for_ollama_uses_env_model():
    assert model_for("ollama", {"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_model_for_cloud_uses_default_model():
    assert model_for("gemini", {}) == "gemini/gemini-2.5-flash"


def test_demo_provider_prefers_cloud_over_ollama():
    # temperature 0.0에서 멈추는 로컬 모델 대신 클라우드를 우선한다
    assert demo_provider(["ollama", "gemini"]) == "gemini"
    assert demo_provider(["gemini", "ollama"]) == "gemini"


def test_demo_provider_falls_back_to_ollama_when_only_local():
    assert demo_provider(["ollama"]) == "ollama"
