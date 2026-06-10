"""S4 lec05 운영 신뢰성 테스트.

예산·재시도·폴백·타임아웃을 결정적으로 본다. 모델 없이 가짜 호출로 검증한다.
"""

import asyncio

import pytest

from section4.lec05.reliability import (
    Budget,
    BudgetError,
    RateLimitError,
    with_fallback,
    with_retry,
    with_timeout,
)


def test_budget_tracks_and_limits():
    budget = Budget(1000)
    budget.charge(400)
    assert budget.remaining() == 600
    budget.charge(400)
    with pytest.raises(BudgetError):
        budget.charge(400)


def test_with_retry_recovers_after_failures():
    state = {"n": 0}

    async def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    assert asyncio.run(with_retry(flaky, base_delay=0)) == "ok"
    assert state["n"] == 3


def test_with_retry_raises_after_max():
    async def always_fail():
        raise RateLimitError("429")

    with pytest.raises(RateLimitError):
        asyncio.run(with_retry(always_fail, max_attempts=3, base_delay=0))


def test_with_fallback_uses_next():
    async def a():
        raise RateLimitError("a")

    async def b():
        return "b"

    assert asyncio.run(with_fallback([a, b])) == "b"


def test_with_fallback_raises_if_all_fail():
    async def a():
        raise RateLimitError("a")

    async def b():
        raise RateLimitError("b")

    with pytest.raises(RateLimitError):
        asyncio.run(with_fallback([a, b]))


def test_with_timeout_cuts_slow_and_passes_fast():
    async def slow():
        await asyncio.sleep(1)

    async def fast():
        return "fast"

    with pytest.raises(TimeoutError):
        asyncio.run(with_timeout(slow, seconds=0.05))
    assert asyncio.run(with_timeout(fast, seconds=1)) == "fast"
