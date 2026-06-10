"""S4 lec01 컨텍스트 어셈블러 테스트.

조립·토큰·순서·압축 전략 같은 순수 로직을 본다. 검색(임베더)·요약(LLM)·예산 깎기의 전체 흐름은
예제로 확인한다.
"""

import asyncio

from section4.lec01.context_assembler import (
    _build_user,
    _order_edges,
    _truncate,
    assemble,
    compact_old,
    count_tokens,
)


def test_build_user_includes_four_parts():
    user = _build_user(["청크A"], "요약B", [("user", "안녕")], "질문C")
    assert "청크A" in user
    assert "요약B" in user
    assert "안녕" in user
    assert "질문C" in user
    assert "[근거]" in user
    assert "[질문]" in user


def test_count_tokens_grows_with_length():
    assert count_tokens("안녕하세요") > 0
    assert count_tokens("긴 문장입니다. " * 20) > count_tokens("짧은 문장")


def test_order_edges_puts_top_at_both_ends():
    assert _order_edges(["A", "B", "C", "D"]) == ["A", "C", "D", "B"]
    assert _order_edges(["A"]) == ["A"]
    assert _order_edges(["A", "B"]) == ["A", "B"]


def test_truncate_keeps_most_recent():
    old = [("user", "옛1"), ("assistant", "옛2"), ("user", "최근")]
    assert _truncate(old, 1) == "user: 최근"


def test_compact_old_truncate_strategy_no_llm():
    old = [("user", "a"), ("assistant", "b"), ("user", "c")]
    assert asyncio.run(compact_old(old, "truncate", "질문")) == "assistant: b\nuser: c"


def test_assemble_is_coroutine():
    assert asyncio.iscoroutinefunction(assemble)
