"""lec03 geocode 도구 테스트. 스키마와 코루틴 여부만 본다. 실제 검색은 예제로 확인한다."""

import asyncio

from section3.lec03.tools.geocode import SCHEMA, geocode


def test_schema_and_coroutine():
    assert SCHEMA["function"]["name"] == "geocode"
    assert SCHEMA["function"]["parameters"]["required"] == ["name"]
    assert asyncio.iscoroutinefunction(geocode)
