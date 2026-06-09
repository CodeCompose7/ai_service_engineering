"""lec04 — 두 번째 MCP 서버 (계산기).

메모 서버와 도메인이 다른 작은 서버다. 에이전트가 이 서버와 메모 서버에 동시에 붙어, 두 서버의
도구를 한 목록으로 합쳐 쓰는 것을 보인다. 실제로는 파일시스템·GitHub 같은 여러 MCP 서버를 같은
방식으로 꽂는다.

직접 실행하면 stdio로 손님을 기다린다. 보통은 에이전트가 자식 프로세스로 띄운다.
    uv run python src/section3/lec04/mcp_server_calc.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("calc")


@mcp.tool()
def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """두 수를 곱한다."""
    return a * b


if __name__ == "__main__":
    mcp.run()
