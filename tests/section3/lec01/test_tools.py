"""lec01 도구들의 순수 로직 테스트. LLM 없이 도구 자체와 등록을 검증한다."""

import re

import pytest

from section3.lec01.tools import TOOLS, run_tool
from section3.lec01.tools.calculator import calculate
from section3.lec01.tools.clock import current_time
from section3.lec01.tools.glossary import lookup_term


def test_calculate_four_ops():
    assert calculate(6, 3, "add") == 9
    assert calculate(6, 3, "subtract") == 3
    assert calculate(6, 3, "multiply") == 18
    assert calculate(6, 3, "divide") == 2


def test_calculate_divide_by_zero_is_none():
    assert calculate(1, 0, "divide") is None


def test_current_time_format():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", current_time())


def test_lookup_term_found_and_loose():
    assert "검색 증강" in lookup_term("RAG")
    assert "벡터" in lookup_term("임베딩이 뭐야")  # 구절로 물어도 느슨히 매칭


def test_lookup_term_not_found():
    assert lookup_term("없는용어") == "사전에 없는 용어입니다."


def test_tools_registry_has_four_schemas():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {"calculate", "current_time", "lookup_term", "search_wikipedia"}


def test_search_wikipedia_schema_shape():
    # 실행은 네트워크·LLM이 필요해 예제로 확인하고, 여기서는 스키마만 본다
    wiki = next(t for t in TOOLS if t["function"]["name"] == "search_wikipedia")
    assert wiki["function"]["parameters"]["required"] == ["query"]


def test_run_tool_dispatches_each():
    assert run_tool("calculate", {"a": 73654, "b": 8921, "op": "multiply"}) == 657067334
    assert run_tool("lookup_term", {"term": "에이전트"}).startswith("모델이")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", run_tool("current_time", {}))


def test_run_tool_unknown_raises():
    with pytest.raises(ValueError):
        run_tool("없는도구", {})
