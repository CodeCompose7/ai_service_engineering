"""lec07 자기수정 테스트.

비평이 만족 신호인지 보는 판정만 본다. 초안·비평·수정의 전체 루프는 모델이 필요해 예제로 확인한다.
"""

import asyncio

from section3.lec07.reflection import _is_satisfied, run


def test_is_satisfied_on_ok():
    assert _is_satisfied("OK")
    assert _is_satisfied("  ok, 더 고칠 게 없다")


def test_not_satisfied_when_critique_present():
    assert not _is_satisfied("타입 검증이 빠졌습니다")


def test_run_is_coroutine():
    assert asyncio.iscoroutinefunction(run)
