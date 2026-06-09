"""lec07 — 자기수정 에이전트 (reflection), LangGraph로.

초안→비평→수정을 그래프로 짠다. generate에서 초안을 만들고 reflect에서 비평한다. 충분히 좋거나
정해진 횟수에 이르면 끝내고, 아니면 revise로 고친 뒤 다시 reflect로 돌아온다. lec06의 조건 엣지와
되돌아오는 루프 그대로다. 흐름이 for·if가 아니라 그래프로 드러나고, 그래프가 스스로 그려진다.

자기수정은 패턴이라 plain 루프로도 짤 수 있지만, 루프·분기가 또렷한 LangGraph가 잘 맞는다.

실행:
    uv run python src/section3/lec07/reflection.py
"""

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from section3.lec02.async_llm import acomplete

WRITER = "주어진 과제를 푼다. 파이썬 코드를 요청하면 코드만 낸다."
CRITIC = (
    "초안의 약점을 두세 가지 짚는다. 에러 처리·엣지 케이스·효율·가독성을 본다. "
    "더 고칠 게 없으면 첫 줄에 OK라고만 답한다."
)
REVISER = "비평을 반영해 초안을 고친다. 설명 없이 고친 결과만 낸다."
MAX_ROUNDS = 2


class State(TypedDict):
    task: str
    draft: str
    critique: str
    rounds: int


def _msg(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _is_satisfied(critique: str) -> bool:
    """비평이 OK로 시작하면 더 고칠 게 없다는 신호다."""
    return critique.strip().upper().startswith("OK")


async def generate(state: State) -> dict:
    """초안을 만든다."""
    return {"draft": await acomplete(_msg(WRITER, state["task"]))}


async def reflect(state: State) -> dict:
    """초안을 비평한다."""
    user = f"과제: {state['task']}\n초안:\n{state['draft']}"
    return {"critique": await acomplete(_msg(CRITIC, user))}


async def revise(state: State) -> dict:
    """비평을 반영해 초안을 고치고, 횟수를 한 번 올린다."""
    user = f"과제: {state['task']}\n초안:\n{state['draft']}\n비평:\n{state['critique']}"
    return {"draft": await acomplete(_msg(REVISER, user)), "rounds": state["rounds"] + 1}


def route(state: State) -> str:
    """조건 엣지 — 만족하거나 횟수가 차면 끝내고, 아니면 다시 고친다."""
    if _is_satisfied(state["critique"]) or state["rounds"] >= MAX_ROUNDS:
        return END
    return "revise"


def build_graph():
    """generate → reflect → (revise 루프 또는 END)로 자기수정 그래프를 짠다."""
    graph = StateGraph(State)
    graph.add_node("generate", generate)
    graph.add_node("reflect", reflect)
    graph.add_node("revise", revise)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "reflect")
    graph.add_conditional_edges("reflect", route, {"revise": "revise", END: END})
    graph.add_edge("revise", "reflect")
    return graph.compile()


APP = build_graph()


async def run(task: str) -> str:
    """그래프를 돌리며 노드별 진행을 보이고, 마지막 초안을 돌려준다."""
    draft = ""
    initial = {"task": task, "draft": "", "critique": "", "rounds": 0}
    async for update in APP.astream(initial, stream_mode="updates"):
        for node, delta in update.items():
            if "draft" in delta:
                draft = delta["draft"]
                print(f"  [{node}] 초안 갱신")
            if "critique" in delta:
                tag = "OK" if _is_satisfied(delta["critique"]) else "고칠 점 있음"
                print(f"  [{node}] 비평 → {tag}")
    return draft


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("그래프 구조 (LangGraph가 그린 mermaid):")
    print(APP.get_graph().draw_mermaid())
    task = "파이썬으로 두 정수의 최대공약수를 구하는 함수를 작성해줘."
    print(f"\n과제: {task}")
    final = asyncio.run(run(task))
    print(f"\n최종:\n{final.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
