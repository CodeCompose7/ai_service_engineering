"""lec07 — 계획 수립 에이전트 (plan-and-execute), LangGraph로.

먼저 과제를 단계로 쪼개는 계획을 세우고, 그 계획대로 단계를 차례로 실행한 뒤, 결과를 종합한다.
반응형이 매 스텝 즉흥으로 가는 것과 달리, 길을 먼저 그려 두고 간다.

그래프로 짠다. planner가 계획을 만들고, executor가 단계를 하나씩 처리하며 자기 자신으로 되돌아온다
(lec06의 카운터 루프). 단계가 다 끝나면 synthesize로 간다. 단계는 앞 결과에 기대므로 순차다.
lec06의 도시들이 서로 독립이라 Send로 병렬이던 것과 대비된다.

계획 수립도 패턴이라 plain 루프로 짤 수 있지만, 루프가 또렷한 LangGraph가 잘 맞는다.

실행:
    uv run python src/section3/lec07/plan_execute.py
"""

import asyncio
import operator
import re
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from section3.lec02.async_llm import acomplete

PLANNER = "과제를 3~4개의 짧은 단계로 쪼갠다. 한 줄에 한 단계만, 번호 없이 쓴다."
EXECUTOR = "계획의 한 단계를 수행한다. 앞 결과를 참고해 이번 단계만 두세 문장으로 처리한다."
SYNTH = "단계 결과들을 매끄러운 한 편의 글로 합친다. 군더더기 없이 쓴다."


class State(TypedDict):
    task: str
    plan: list[str]
    step: int
    results: Annotated[list, operator.add]
    final: str


def _msg(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse_plan(text: str) -> list[str]:
    """계획 텍스트를 단계 목록으로 자른다. 빈 줄을 버리고 앞머리 불릿·번호만 떼낸다."""
    steps = []
    for line in text.splitlines():
        cleaned = re.sub(r"^[\s\-•*]+", "", line)
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned)
        if cleaned.strip():
            steps.append(cleaned.strip())
    return steps


async def planner(state: State) -> dict:
    """과제를 단계 목록으로 쪼갠다."""
    return {
        "plan": _parse_plan(await acomplete(_msg(PLANNER, state["task"]))),
    }


async def executor(state: State) -> dict:
    """현재 단계를 실행하고, step을 한 칸 민다."""
    step = state["plan"][state["step"]]
    done = "\n".join(
        f"- {s}: {r}"
        for s, r in zip(
            state["plan"],
            state["results"],
            strict=False,
        )
    )
    user = f"과제: {state['task']}\n지금까지:\n{done or '(아직 없음)'}\n이번 단계: {step}"
    out = await acomplete(_msg(EXECUTOR, user))
    return {
        "results": [out.replace("\n", " ").strip()],
        "step": state["step"] + 1,
    }


async def synthesize(state: State) -> dict:
    """단계 결과들을 한 편의 글로 합친다."""
    joined = "\n".join(
        f"{i}. {s}\n   {r}"
        for i, (s, r) in enumerate(
            zip(state["plan"], state["results"], strict=True),
            1,
        )
    )
    return {
        "final": await acomplete(_msg(SYNTH, f"과제: {state['task']}\n\n{joined}")),
    }


def route(state: State) -> str:
    """조건 엣지 — 단계가 남았으면 executor로 되돌아가고, 끝났으면 종합으로 간다."""
    return "executor" if state["step"] < len(state["plan"]) else "synthesize"


def build_graph():
    """planner → executor 루프 → synthesize로 계획 수립 그래프를 짠다."""
    graph = StateGraph(State)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        route,
        {
            "executor": "executor",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("synthesize", END)
    return graph.compile()


APP = build_graph()


async def run(task: str) -> dict:
    """그래프를 돌리며 계획과 단계 진행을 보이고, 종합 결과를 돌려준다."""
    plan, final = [], ""
    initial = {"task": task, "plan": [], "step": 0, "results": [], "final": ""}
    async for update in APP.astream(initial, stream_mode="updates"):
        for node, delta in update.items():
            if node == "planner":
                plan = delta["plan"]
                print(f"  [planner] {len(plan)}단계 계획 수립")
            elif node == "executor":
                print(f"  [executor] {delta['step']}단계까지 실행")
            elif node == "synthesize":
                final = delta["final"]
                print("  [synthesize] 종합")
    return {"plan": plan, "final": final}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("그래프 구조 (LangGraph가 그린 mermaid):")
    print(APP.get_graph().draw_mermaid())
    task = "초보자에게 RAG가 무엇인지 설명하는 짧은 글을 써줘."
    print(f"\n과제: {task}")
    result = asyncio.run(run(task))
    print("\n세운 계획:")
    for i, step in enumerate(result["plan"], 1):
        print(f"  {i}. {step}")
    print(f"\n종합한 글:\n{result['final']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
