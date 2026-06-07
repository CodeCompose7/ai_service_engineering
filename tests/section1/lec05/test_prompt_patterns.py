"""lec05 prompt_patterns의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(프로바이더 탐지·모델 문자열·프롬프트 구성)만 검증한다.
"""

from section1.lec05.prompt_patterns import (
    CATEGORIES,
    api_base_kwargs,
    available_providers,
    bare_classify,
    designed_classify,
    model_for,
    sentiment_messages,
    target_providers,
)


def test_available_providers_detects_filled_keys_only():
    env = {"GEMINI_API_KEY": "x", "OLLAMA_API_BASE": "http://h:11434"}
    assert available_providers(env) == ["gemini", "ollama"]


def test_target_providers_keeps_fixed_order():
    assert target_providers(["ollama", "gemini"]) == ["gemini", "ollama"]


def test_bare_classify_is_single_user_message():
    msgs = bare_classify("물건이 안 와요")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "물건이 안 와요" in msgs[0]["content"]


def test_designed_classify_puts_rules_in_system():
    msgs = designed_classify("물건이 안 와요")
    assert [m["role"] for m in msgs] == ["system", "user"]
    # 허용 카테고리가 system에 모두 들어간다
    for category in CATEGORIES:
        assert category in msgs[0]["content"]
    assert msgs[1]["content"] == "물건이 안 와요"


def test_sentiment_zero_shot_has_no_examples():
    msgs = sentiment_messages("무난해요", with_examples=False)
    # system 하나 + user 하나
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[-1]["content"] == "무난해요"


def test_sentiment_few_shot_inserts_example_pairs():
    msgs = sentiment_messages("무난해요", with_examples=True)
    # system + (user, assistant) 쌍 둘 + 마지막 user
    assert [m["role"] for m in msgs] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
    ]
    assert msgs[-1]["content"] == "무난해요"
    # 예시 라벨이 assistant 자리에 들어간다
    assert msgs[2]["content"] == "긍정"
    assert msgs[4]["content"] == "부정"


def test_model_for_ollama_uses_env_model():
    assert model_for("ollama", {"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_model_for_cloud_uses_default_model():
    assert model_for("gemini", {}) == "gemini/gemini-2.5-flash"


def test_api_base_kwargs_ollama_uses_base():
    assert api_base_kwargs("ollama", {"OLLAMA_API_BASE": "http://h:11434"}) == {
        "api_base": "http://h:11434"
    }


def test_api_base_kwargs_cloud_is_empty():
    assert api_base_kwargs("gemini", {}) == {}
