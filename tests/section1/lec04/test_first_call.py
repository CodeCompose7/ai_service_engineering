"""lec04 first_call의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(프로바이더 탐지·대상 선정·메시지 구성·모델 문자열)만 검증한다.
"""

from section1.lec04.first_call import (
    api_base_kwargs,
    available_providers,
    build_messages,
    conversation,
    model_for,
    target_providers,
)


def test_available_providers_detects_filled_keys_only():
    env = {
        "GEMINI_API_KEY": "x",
        "OLLAMA_API_BASE": "http://host.docker.internal:11434",
    }
    assert available_providers(env) == ["gemini", "ollama"]


def test_available_providers_empty_env():
    assert available_providers({}) == []


def test_target_providers_keeps_fixed_order():
    # 탐지 순서와 무관하게 gemini, ollama 순으로 추린다
    assert target_providers(["ollama", "gemini"]) == ["gemini", "ollama"]


def test_target_providers_filters_unavailable():
    assert target_providers(["gemini"]) == ["gemini"]
    assert target_providers([]) == []


def test_build_messages_with_system():
    msgs = build_messages("지시", "질문")
    assert msgs == [
        {"role": "system", "content": "지시"},
        {"role": "user", "content": "질문"},
    ]


def test_build_messages_without_system():
    msgs = build_messages(None, "질문")
    assert msgs == [{"role": "user", "content": "질문"}]


def test_conversation_expands_turns_in_order():
    msgs = conversation([("user", "안녕"), ("assistant", "반가워"), ("user", "잘 가")])
    assert msgs == [
        {"role": "user", "content": "안녕"},
        {"role": "assistant", "content": "반가워"},
        {"role": "user", "content": "잘 가"},
    ]


def test_model_for_ollama_uses_env_model():
    assert model_for("ollama", {"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_model_for_cloud_uses_default_model():
    assert model_for("gemini", {}) == "gemini/gemini-2.5-flash"


def test_api_base_kwargs_ollama_uses_base():
    kwargs = api_base_kwargs("ollama", {"OLLAMA_API_BASE": "http://h:11434"})
    assert kwargs == {"api_base": "http://h:11434"}


def test_api_base_kwargs_cloud_is_empty():
    assert api_base_kwargs("gemini", {}) == {}
