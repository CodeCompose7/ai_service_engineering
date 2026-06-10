"""S4 lec06 평가 하네스 테스트.

점수 집계와 테스트셋 실행을 결정적으로 본다. judge·agent는 가짜로 바꿔 모델 없이 검증한다.
"""

import asyncio

from section4.lec06.evaluate import TESTSET, EvalHarness, _score


def test_score_is_pass_rate():
    assert _score([{"passed": True}, {"passed": False}]) == 0.5
    assert _score([{"passed": True}, {"passed": True}]) == 1.0
    assert _score([]) == 0.0


def test_eval_harness_runs_testset_with_fakes():
    async def fake_answer(question):
        return "답"

    async def fake_judge(question, answer, criteria):
        return "환불" in question  # 첫 케이스만 통과시키는 가짜 채점

    harness = EvalHarness(TESTSET, judge_fn=fake_judge)
    result = asyncio.run(harness.run(fake_answer))
    assert len(result["results"]) == len(TESTSET)
    assert result["results"][0]["passed"] is True
    assert 0 <= result["score"] <= 1
