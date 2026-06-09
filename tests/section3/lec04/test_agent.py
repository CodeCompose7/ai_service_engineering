"""lec04 MCP 연결 에이전트 테스트.

MCP 도구를 function 스키마로 옮기고 결과 텍스트를 모으는 변환 로직만 본다. 서버에 붙어 도구를
발견·호출하는 흐름은 모델·자식 프로세스가 필요해 예제 실행으로 확인한다.
"""

from types import SimpleNamespace

from section3.lec04.agent import _result_text, _to_schema


def test_to_schema_wraps_mcp_tool():
    tool = SimpleNamespace(
        name="save_memo",
        description="메모를 저장한다",
        inputSchema={"type": "object", "properties": {"text": {"type": "string"}}},
    )
    schema = _to_schema(tool)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "save_memo"
    assert schema["function"]["parameters"] == tool.inputSchema


def test_result_text_joins_text_parts():
    content = [
        SimpleNamespace(type="text", text="첫"),
        SimpleNamespace(type="text", text="둘째"),
    ]
    result = SimpleNamespace(content=content)
    assert _result_text(result) == "첫\n둘째"
