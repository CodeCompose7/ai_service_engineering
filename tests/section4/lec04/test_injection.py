"""S4 lec04 프롬프트 주입 방어 테스트.

방어 체크리스트와 시그니처를 본다. 탐지·요약 자체는 모델이 필요해 예제로 확인한다.
"""

import asyncio

from section4.lec04.injection import CHECKLIST, detect_injection, safe_summarize


def test_checklist_has_core_defenses():
    assert len(CHECKLIST) >= 4
    joined = " ".join(CHECKLIST)
    assert "데이터" in joined
    assert "최소 권한" in joined


def test_detect_injection_is_coroutine():
    assert asyncio.iscoroutinefunction(detect_injection)


def test_safe_summarize_is_coroutine():
    assert asyncio.iscoroutinefunction(safe_summarize)
