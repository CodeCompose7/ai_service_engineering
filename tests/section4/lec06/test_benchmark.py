"""S4 lec06 다중 에이전트 벤치마크 테스트.

평균·상대 비용 집계를 결정적으로 본다. 에이전트·채점은 가짜로 바꿔 모델 없이 검증한다.
"""

import asyncio

from section4.lec06.benchmark import _mean, benchmark


def test_mean():
    assert _mean([1, 2, 3]) == 2
    assert _mean([]) == 0.0


def test_benchmark_quality_and_relative_cost(monkeypatch):
    async def cheap(question):
        return {"answer": "a", "in": 10, "out": 5}

    async def pricey(question):
        return {"answer": "a", "in": 100, "out": 50}

    async def fake_score(question, answer, criteria):
        return 4

    monkeypatch.setattr("section4.lec06.benchmark.score", fake_score)
    rows = asyncio.run(
        benchmark([("싼것", cheap), ("비싼것", pricey)], [{"q": "x", "criteria": "y"}])
    )
    assert rows[0]["quality"] == 4
    assert rows[0]["rel_cost"] == 1.0  # 최저가 기준 1.0배
    assert rows[1]["rel_cost"] > 1.0
