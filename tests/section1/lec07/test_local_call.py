"""lec07 local_call의 순수 로직 테스트.

네트워크나 키 없이 도는 부분(백엔드 탐지·모델 문자열·호출 인자)만 검증한다.
"""

from section1.lec07.local_call import (
    CLOUD_MODEL,
    have_cloud,
    have_local,
    local_model,
    ollama_kwargs,
    targets,
)


def test_have_cloud_and_local_read_env():
    assert have_cloud({"GEMINI_API_KEY": "x"}) is True
    assert have_cloud({}) is False
    assert have_local({"OLLAMA_API_BASE": "http://h:11434"}) is True
    assert have_local({}) is False


def test_local_model_uses_env_model():
    assert local_model({"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_local_model_falls_back_to_default():
    assert local_model({}).startswith("ollama/")


def test_ollama_kwargs_passes_api_base():
    assert ollama_kwargs({"OLLAMA_API_BASE": "http://h:11434"}) == {"api_base": "http://h:11434"}


def test_targets_includes_both_when_available():
    env = {"GEMINI_API_KEY": "x", "OLLAMA_API_BASE": "http://h:11434", "OLLAMA_MODEL": "gemma4:12b"}
    result = targets(env)
    assert [label for label, _, _ in result] == ["클라우드", "로컬"]
    assert result[0][1] == CLOUD_MODEL
    assert result[1][1] == "ollama/gemma4:12b"
    assert result[1][2] == {"api_base": "http://h:11434"}


def test_targets_only_local_when_no_cloud_key():
    env = {"OLLAMA_API_BASE": "http://h:11434"}
    result = targets(env)
    assert [label for label, _, _ in result] == ["로컬"]


def test_targets_empty_when_nothing_ready():
    assert targets({}) == []
