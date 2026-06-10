"""S4 lec05 운영 신뢰성 하네스 테스트.

예산 거부·폴백·전체 실패를 결정적으로 본다. 가짜 모델로 모델 없이 검증한다.
"""

import asyncio

from section4.lec05.reliability import Budget, RateLimitError
from section4.lec05.reliable_agent import ReliableAgent


def test_budget_exceeded_refuses_without_calling_model():
    called = {"n": 0}

    async def model(messages):
        called["n"] += 1
        return "ok"

    agent = ReliableAgent([("m", model)], Budget(1))  # 1토큰 한도
    result = asyncio.run(agent.ask([{"role": "user", "content": "이건 1토큰보다 긴 질문이다"}]))
    assert "거부" in result["reply"]
    assert called["n"] == 0  # 예산에서 막혀 모델을 부르지 않는다


def test_falls_back_to_next_model():
    async def flaky(messages):
        raise RateLimitError("429")

    async def good(messages):
        return "보조 응답"

    agent = ReliableAgent([("주", flaky), ("보조", good)], Budget(100000), retries=2)
    result = asyncio.run(agent.ask([{"role": "user", "content": "hi"}]))
    assert result["reply"] == "보조 응답"
    assert any("폴백" in step for step in result["trace"])


def test_all_candidates_fail_returns_message():
    async def flaky(messages):
        raise RateLimitError("429")

    agent = ReliableAgent([("a", flaky), ("b", flaky)], Budget(100000), retries=2)
    result = asyncio.run(agent.ask([{"role": "user", "content": "hi"}]))
    assert "응답할 수 없" in result["reply"]
    assert "모든 후보 실패" in result["trace"]
