"""S4 lec01 컨텍스트 어셈블러 테스트.

조립과 토큰 측정 같은 순수 로직을 본다. 검색(임베더)·압축(LLM)·예산 깎기의 전체 흐름은 예제로
확인한다.
"""

import asyncio

from section4.lec01.context_assembler import _build_user, assemble, count_tokens


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


def test_assemble_is_coroutine():
    assert asyncio.iscoroutinefunction(assemble)
