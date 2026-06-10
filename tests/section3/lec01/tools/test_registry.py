"""tools 등록(__init__) 테스트 — TOOLS 목록과 run_tool 디스패치."""

import re

import pytest

from section3.lec01.tools import TOOLS, run_tool


def test_registry_has_four_schemas():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {"calculate", "current_time", "lookup_term", "search_wikipedia"}


def test_run_tool_dispatches_pure_tools():
    assert run_tool("calculate", {"a": 73654, "b": 8921, "op": "multiply"}) == 657067334
    assert run_tool("lookup_term", {"term": "에이전트"}).startswith("모델이")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", run_tool("current_time", {}))


def test_run_tool_unknown_raises():
    with pytest.raises(ValueError):
        run_tool("없는도구", {})
