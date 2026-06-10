"""lec02 비동기 에이전트 테스트. 루프는 모델이 필요해 예제 실행으로 확인한다."""

import asyncio

from section3.lec02.async_agent import run_agent_async, wiki_agent_async


def test_agent_fns_are_coroutines():
    assert asyncio.iscoroutinefunction(run_agent_async)
    assert asyncio.iscoroutinefunction(wiki_agent_async)
