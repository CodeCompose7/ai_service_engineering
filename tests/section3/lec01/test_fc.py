"""lec01 function calling의 순수 로직 테스트.

도구 실행·디스패치·스키마·프로바이더 해석을 LLM 없이 검증한다. 실제 도구 호출 loop는
모델이 필요해 예제 실행으로 확인한다.
"""

import pytest

from section3.lec01.fc import TOOLS, calculate, resolve_model, run_tool


def test_calculate_four_ops():
    assert calculate(6, 3, "add") == 9
    assert calculate(6, 3, "subtract") == 3
    assert calculate(6, 3, "multiply") == 18
    assert calculate(6, 3, "divide") == 2


def test_calculate_divide_by_zero_is_none():
    assert calculate(1, 0, "divide") is None


def test_run_tool_dispatches_calculate():
    assert run_tool("calculate", {"a": 73654, "b": 8921, "op": "multiply"}) == 657067334


def test_run_tool_unknown_raises():
    with pytest.raises(ValueError):
        run_tool("없는도구", {})


def test_tools_schema_shape():
    fn = TOOLS[0]["function"]
    assert fn["name"] == "calculate"
    assert fn["parameters"]["required"] == ["a", "b", "op"]
    assert fn["parameters"]["properties"]["op"]["enum"] == ["add", "subtract", "multiply", "divide"]


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
