"""lec02 단일 도구 에이전트 테스트.

도구 등록·디스패치만 검증한다. 도구를 반복 호출하는 에이전트 루프는 모델이 필요해 예제
실행으로 확인한다.
"""

import pytest

from section3.lec02.agent import TOOLS, run_tool


def test_tools_has_only_calculate():
    assert [t["function"]["name"] for t in TOOLS] == ["calculate"]  # 단일 도구


def test_run_tool_calculate():
    assert run_tool("calculate", {"a": 12, "b": 8, "op": "add"}) == 20


def test_run_tool_unknown_raises():
    with pytest.raises(ValueError):
        run_tool("없는도구", {})
