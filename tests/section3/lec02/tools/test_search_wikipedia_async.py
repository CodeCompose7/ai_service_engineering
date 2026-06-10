"""lec02 비동기 위키 도구 테스트.

스키마와 도구가 코루틴인지만 본다. 네트워크·LLM을 거치는 실제 검색은 예제 실행으로 확인한다.
"""

import asyncio

from section3.lec02.tools import SCHEMA, search_wikipedia_async


def test_schema_is_search_wikipedia():
    assert SCHEMA["function"]["name"] == "search_wikipedia"
    assert SCHEMA["function"]["parameters"]["required"] == ["query"]


def test_tool_is_coroutine():
    assert asyncio.iscoroutinefunction(search_wikipedia_async)
