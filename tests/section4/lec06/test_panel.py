"""S4 lec06 멀티 저지 패널 테스트.

다수결 집계를 결정적으로 본다. 저지 호출 자체는 모델이 필요해 예제로 확인한다.
"""

import asyncio

from section4.lec06.panel import _aggregate, panel_judge


def test_aggregate_majority_pass():
    result = _aggregate({"엄격": True, "관대": True, "사용자": False})
    assert result["agreement"] == 2
    assert result["passed"] is True


def test_aggregate_majority_fail():
    result = _aggregate({"엄격": False, "관대": True, "사용자": False})
    assert result["agreement"] == 1
    assert result["passed"] is False


def test_panel_judge_is_coroutine():
    assert asyncio.iscoroutinefunction(panel_judge)
