"""S4 lec02 내용 검열 하네스 테스트.

regex 차단 목록의 한계를 못박는다. LLM 검열 자체는 모델이 필요해 예제로 확인한다.
"""

import asyncio

from section4.lec02.harness3 import ModeratedHarness, llm_moderate, regex_flag


def test_regex_catches_listed_word():
    assert regex_flag("야 이 쓰레기야") is True


def test_regex_misses_obfuscation():
    # regex의 한계: 띄어쓰기로 비틀면 놓친다. 그래서 LLM 검열이 필요하다.
    assert regex_flag("야 이 쓰 레 기야") is False


def test_regex_passes_clean():
    assert regex_flag("오늘 날씨 어때?") is False


def test_llm_moderate_is_coroutine():
    assert asyncio.iscoroutinefunction(llm_moderate)


def test_run_is_coroutine():
    assert asyncio.iscoroutinefunction(ModeratedHarness().run)
