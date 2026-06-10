"""lec04 계산기 MCP 서버 도구 테스트. FastMCP 도구는 그대로 호출 가능하다."""

from section3.lec04.mcp_server_calc import add, multiply


def test_add():
    assert add(3, 4) == 7


def test_multiply():
    assert multiply(12, 8) == 96
