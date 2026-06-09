"""lec04 — MCP 서버 (메모 서비스).

FastMCP로 도구를 노출하는 작은 MCP 서버다. 에이전트는 이 서버에 stdio로 붙어 list_tools로 도구를
발견하고, call_tool로 부른다. 도구를 에이전트 코드에 박는 대신, 별도 프로세스(서비스)로 띄워 표준
규격으로 연결한다.

메모를 모아 두는 상태를 가진다. 같은 세션 동안 save_memo로 쌓고 list_memos로 본다. 서버가 살아
있는 서비스임을 보인다.

직접 실행하면 stdio로 손님을 기다린다. 보통은 에이전트가 자식 프로세스로 띄운다.
    uv run python src/section3/lec04/mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("memo")
_memos: list[str] = []


@mcp.tool()
def save_memo(text: str) -> str:
    """메모 한 줄을 저장한다."""
    _memos.append(text)
    return f"저장했습니다. 현재 {len(_memos)}개."


@mcp.tool()
def list_memos() -> list[str]:
    """저장된 메모를 모두 돌려준다."""
    return list(_memos)


@mcp.resource("memo://all")
def all_memos() -> str:
    """저장된 메모 전체를 읽기 전용 리소스로 노출한다.

    도구가 '행동'(저장)이라면, 리소스는 '데이터'다. 클라이언트가 read_resource로 가져와 맥락에
    넣을 수 있다. 부수효과 없이 읽기만 한다.
    """
    return "\n".join(f"- {m}" for m in _memos) or "(아직 메모가 없습니다)"


if __name__ == "__main__":
    mcp.run()
