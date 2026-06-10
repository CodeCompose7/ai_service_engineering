"""S4 lec06 실제 RAG 평가 테스트.

테스트셋 구조와 answer_fn 시그니처를 본다. RAG·judge 전체 실행은 인덱스·모델이 필요해 예제로
확인한다.
"""

import asyncio

from section4.lec06.rag_eval import TESTSET, model_only, rag_answer


def test_testset_has_question_and_criteria():
    assert len(TESTSET) >= 1
    for case in TESTSET:
        assert "q" in case
        assert "criteria" in case


def test_answer_fns_are_coroutines():
    assert asyncio.iscoroutinefunction(rag_answer)
    assert asyncio.iscoroutinefunction(model_only)
