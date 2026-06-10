"""lec03 멀티툴 에이전트 테스트.

도구 결과를 메시지용 JSON으로 바꾸는 _call(dataclass→asdict, 에러 처리)을 결정적인 쇼핑
도구로 검증한다. 라우팅 루프 자체는 모델이 필요해 예제로 확인한다.
"""

import asyncio
import json

from section3.lec03.agent import _call, run_agent


def test_run_agent_is_coroutine():
    assert asyncio.iscoroutinefunction(run_agent)


def test_call_serializes_dataclass():
    content = asyncio.run(_call("find_user", {"name": "alice"}))
    assert json.loads(content) == {"user_id": "U001"}


def test_call_wraps_tool_error():
    content = asyncio.run(_call("find_user", {"name": "nobody"}))
    assert "error" in json.loads(content)
