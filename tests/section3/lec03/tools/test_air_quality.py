"""lec03 미세먼지 도구 테스트. 등급 계산은 순수 로직이라 검증하고, 실제 호출은 예제로 확인한다."""

import asyncio

from section3.lec03.tools.air_quality import SCHEMA, _grade, get_air_quality


def test_grade_bands():
    assert _grade(10) == "좋음"
    assert _grade(25) == "보통"
    assert _grade(50) == "나쁨"
    assert _grade(100) == "매우 나쁨"


def test_schema_and_coroutine():
    assert SCHEMA["function"]["name"] == "get_air_quality"
    assert asyncio.iscoroutinefunction(get_air_quality)
