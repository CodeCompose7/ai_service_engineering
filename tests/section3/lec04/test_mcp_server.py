"""lec04 MCP 서버 도구 테스트.

FastMCP의 @mcp.tool()은 함수를 그대로 호출 가능하게 두므로, 저장·목록 로직을 직접 검증한다.
서버를 stdio로 띄워 붙는 흐름은 에이전트 예제로 확인한다.
"""

from section3.lec04.mcp_server import all_memos, list_memos, save_memo


def test_save_then_list():
    before = len(list_memos())
    save_memo("회의 메모")
    notes = list_memos()
    assert len(notes) == before + 1
    assert notes[-1] == "회의 메모"


def test_all_memos_resource_reflects_saves():
    save_memo("리소스 확인용")
    text = all_memos()
    assert "리소스 확인용" in text
