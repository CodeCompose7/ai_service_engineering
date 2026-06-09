"""lec05 — LangGraph 기초 (최소 그래프).

lec02~03에서 손으로 짠 제어 루프(model → tools → model …)를 LangGraph의 StateGraph로 옮긴다.
도구는 lec03 것을 그대로 쓴다. 바뀌는 것은 흐름의 표현뿐이다. for 루프가 아니라 노드와 엣지로
흐름이 드러나고, 그래프가 스스로 다이어그램을 그려 준다.

- 상태(State): messages를 리듀서로 누적한다.
- 노드: model(LLM 호출), tools(도구 실행).
- 엣지: START→model, model→(조건)→tools 또는 END, tools→model(루프).

실행:
    uv run python src/section3/lec05/graph.py
"""

import asyncio
import json
import operator
from dataclasses import asdict
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from section3.lec01.llm import resolve_model
from section3.lec02.async_llm import acompletion
from section3.lec03.tools import TOOLS, run_tool
from section3.lec03.tools.errors import ToolError

SYSTEM = (
    "너는 여러 도구를 쓰는 도우미다. 질문에 맞는 도구를 골라 부른다. 날씨·미세먼지는 먼저 "
    "geocode로 좌표를 얻어 넘기고, 주문 조회는 find_user로 id를 얻어 이어 간다. "
    "도구 결과만 근거로 한국어로 답한다."
)


class State(TypedDict):
    messages: Annotated[list, operator.add]


async def call_model(state: State) -> dict:
    """model 노드 — 도구 목록과 함께 모델을 부르고, 응답을 상태에 누적한다."""
    model, kwargs = resolve_model()
    resp = await acompletion(model, state["messages"], tools=TOOLS, **kwargs)
    return {"messages": [resp.choices[0].message.model_dump()]}


async def run_tools(state: State) -> dict:
    """tools 노드 — 직전 응답의 도구 호출을 실행해 결과를 상태에 누적한다."""
    results = []
    for call in state["messages"][-1]["tool_calls"]:
        args = json.loads(call["function"]["arguments"])
        try:
            payload = asdict(await run_tool(call["function"]["name"], args))
        except ToolError as exc:
            payload = {"error": str(exc)}
        results.append(
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(payload, ensure_ascii=False),
            }
        )
    return {"messages": results}


def should_continue(state: State) -> str:
    """조건 엣지 — 도구 호출이 남았으면 tools로, 없으면 끝낸다."""
    return "tools" if state["messages"][-1].get("tool_calls") else END


def build_graph():
    """상태·노드·엣지로 최소 에이전트 그래프를 짜고 컴파일한다."""
    graph = StateGraph(State)
    graph.add_node("model", call_model)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")
    return graph.compile()


APP = build_graph()


async def run(task: str) -> dict:
    """그래프를 한 번 돌려, 도구 호출 자취와 최종 답을 추린다."""
    state = await APP.ainvoke(
        {"messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": task},
        ]}
    )
    trace = [
        c["function"]["name"]
        for m in state["messages"]
        if m.get("tool_calls")
        for c in m["tool_calls"]
    ]
    return {"answer": state["messages"][-1]["content"], "trace": trace}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("그래프 구조 (LangGraph가 그린 mermaid):")
    print(APP.get_graph().draw_mermaid())
    for task in ["서울 날씨 알려주고, alice 주문 내역도 보여줘"]:
        result = asyncio.run(run(task))
        print(f"\n질문: {task}")
        print(f"  도구 자취: {result['trace']}")
        print(f"  답: {result['answer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
