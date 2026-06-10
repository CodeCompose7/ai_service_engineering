"""lec03 날씨 도구 테스트. 스키마·코루틴·코드 매핑만 본다. 실제 호출은 예제로 확인한다."""

import asyncio

from section3.lec03.tools.weather import SCHEMA, WMO, get_weather


def test_schema_and_coroutine():
    assert SCHEMA["function"]["name"] == "get_weather"
    assert SCHEMA["function"]["parameters"]["required"] == ["latitude", "longitude"]
    assert asyncio.iscoroutinefunction(get_weather)


def test_wmo_maps_clear():
    assert WMO[0] == "맑음"
