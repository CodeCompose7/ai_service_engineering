"""lec05 LangGraph 기초 테스트.

조건 엣지(should_continue)와 도구 노드(run_tools)의 직렬화, 그래프에 노드가 제대로 들어갔는지를
본다. 모델을 거치는 전체 그래프 실행은 예제로 확인한다.
"""

import asyncio
import json

from langgraph.graph import END

from section3.lec05.graph import APP, memory_demo, run_tools, should_continue, stream_run


def test_should_continue_routes_to_tools():
    state = {"messages": [{"role": "assistant", "tool_calls": [{"id": "1"}]}]}
    assert should_continue(state) == "tools"


def test_should_continue_ends_without_tool_calls():
    state = {"messages": [{"role": "assistant", "content": "끝", "tool_calls": None}]}
    assert should_continue(state) == END


def test_graph_has_model_and_tools_nodes():
    nodes = APP.get_graph().nodes
    assert "model" in nodes
    assert "tools" in nodes


def test_run_tools_executes_lec03_tool_and_serializes():
    fn = {"name": "find_user", "arguments": json.dumps({"name": "alice"})}
    state = {"messages": [{"role": "assistant", "tool_calls": [{"id": "a", "function": fn}]}]}
    out = asyncio.run(run_tools(state))
    msg = out["messages"][0]
    assert msg["role"] == "tool"
    assert json.loads(msg["content"]) == {"user_id": "U001"}
    assert out["tools_used"] == ["find_user"]  # 두 번째 상태 채널도 누적


def test_stream_and_memory_are_coroutines():
    assert asyncio.iscoroutinefunction(stream_run)
    assert asyncio.iscoroutinefunction(memory_demo)
