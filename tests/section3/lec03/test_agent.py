"""lec03 멀티툴 에이전트 테스트. 라우팅 루프는 모델이 필요해 예제로 확인한다."""

import asyncio

from section3.lec03.agent import run_agent


def test_run_agent_is_coroutine():
    assert asyncio.iscoroutinefunction(run_agent)
