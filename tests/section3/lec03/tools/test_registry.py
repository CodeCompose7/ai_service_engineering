"""lec03 도구 레지스트리 테스트. 도구 목록과 이름 기반 디스패치를 본다."""

import asyncio

import pytest

from section3.lec03.tools import TOOLS, run_tool


def test_six_tools_registered():
    names = [t["function"]["name"] for t in TOOLS]
    assert names == [
        "geocode",
        "get_weather",
        "get_air_quality",
        "find_user",
        "get_orders",
        "get_order_detail",
    ]


def test_run_tool_dispatches():
    assert asyncio.run(run_tool("find_user", {"name": "bob"})) == {"user_id": "U002"}


def test_run_tool_unknown_raises():
    with pytest.raises(ValueError):
        asyncio.run(run_tool("없는도구", {}))
