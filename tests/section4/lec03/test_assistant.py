"""S4 lec03 통합 하네스 테스트.

전체 handle 흐름은 모델이 필요해 예제로 확인하고, 여기서는 코루틴·구성만 본다.
"""

import asyncio

from section4.lec03.assistant import GuardedAssistant
from section4.lec03.state import SessionStore


def test_handle_is_coroutine(tmp_path):
    assistant = GuardedAssistant(SessionStore(tmp_path))
    assert asyncio.iscoroutinefunction(assistant.handle)
