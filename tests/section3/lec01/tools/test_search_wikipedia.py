"""search_wikipedia 도구 테스트.

실행은 네트워크와 LLM 호출이 필요해 예제 실행으로 확인하고, 여기서는 스키마만 본다.
"""

from section3.lec01.tools.search_wikipedia import SCHEMA


def test_schema_shape():
    assert SCHEMA["function"]["name"] == "search_wikipedia"
    assert SCHEMA["function"]["parameters"]["required"] == ["query"]
