"""S4 lec04 주입 방어 하네스 테스트.

도구와 시그니처를 본다. 스크리닝 전체 흐름은 모델이 필요해 예제로 확인한다.
"""

import asyncio

from section4.lec04.defended_agent import DefendedAgent, fetch_reviews


def test_fetch_reviews_returns_list():
    reviews = fetch_reviews("위젯")
    assert isinstance(reviews, list)
    assert len(reviews) >= 1


def test_summarize_reviews_is_coroutine():
    assert asyncio.iscoroutinefunction(DefendedAgent().summarize_reviews)
