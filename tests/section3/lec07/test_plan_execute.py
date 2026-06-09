"""lec07 계획 수립 테스트.

계획 텍스트를 단계로 자르는 파싱만 본다. 계획·실행·종합의 전체 흐름은 모델이 필요해 예제로
확인한다.
"""

import asyncio

from section3.lec07.plan_execute import _parse_plan, run


def test_parse_plan_strips_bullets_and_numbers():
    text = "1. 첫 단계\n- 둘째 단계\n• 셋째 단계\n\n   "
    assert _parse_plan(text) == ["첫 단계", "둘째 단계", "셋째 단계"]


def test_parse_plan_keeps_content_numbers():
    assert _parse_plan("3가지 이유를 든다") == ["3가지 이유를 든다"]


def test_run_is_coroutine():
    assert asyncio.iscoroutinefunction(run)
