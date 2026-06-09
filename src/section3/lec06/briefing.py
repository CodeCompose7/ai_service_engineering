"""lec06 — 실전 그래프를 끌어올리기 (병렬·서브그래프·재시도·사람 개입).

graph.py의 순차 루프 자동화를 실전 패턴으로 키운다.

- 병렬 fan-out(Send): 도시를 하나씩 도는 대신, Send로 한꺼번에 흩뿌려 동시에 처리한다.
- 서브그래프: 도시 하나를 처리하는 작은 그래프(city_flow)를 노드로 합성한다.
- 재시도(RetryPolicy): city_flow의 fetch가 일시적 네트워크 오류로 실패하면 자동 재시도한다.
- 사람 개입(interrupt): 브리핑을 발송하기 전에 멈추고 사람의 승인을 받는다. Command로 재개한다.

도구는 lec03, 요약은 lec02 async_llm, 요약 프롬프트·표 포맷은 graph.py 것을 그대로 쓴다.

실행:
    uv run python src/section3/lec06/briefing.py
"""

import asyncio
import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send, interrupt

from section3.lec02.async_llm import acomplete
from section3.lec03.tools.errors import ToolError
from section3.lec03.tools.geocode import geocode
from section3.lec03.tools.weather import get_weather
from section3.lec06.graph import ALERT_SYSTEM, NORMAL_SYSTEM, WARN_KEYWORDS, _as_text


# --- 서브그래프: 도시 하나를 처리한다 (재시도 포함) ---
class CityState(TypedDict):
    city: str
    reports: Annotated[list, operator.add]


async def fetch_city(state: CityState) -> dict:
    """도시 하나의 날씨를 가져온다. 네트워크 오류는 RetryPolicy가 재시도하고, 없는 도시는
    ToolError를 잡아 실패 보고로 남긴다."""
    city = state["city"]
    try:
        loc = await geocode(city)
        weather = await get_weather(loc.latitude, loc.longitude)
        warn = any(k in weather.condition for k in WARN_KEYWORDS)
        report = {
            "city": city,
            "temp_c": weather.temperature_c,
            "condition": weather.condition,
            "warn": warn,
        }
    except ToolError as exc:
        report = {"city": city, "error": str(exc), "warn": False}
    return {"reports": [report]}


def _build_city_flow():
    graph = StateGraph(CityState)
    graph.add_node("fetch", fetch_city, retry=RetryPolicy(max_attempts=3))
    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", END)
    return graph.compile()


CITY_FLOW = _build_city_flow()


# --- 메인 그래프: 병렬 수집 → 사람 승인 → 갈래 요약 ---
class BriefState(TypedDict):
    cities: list[str]
    reports: Annotated[list, operator.add]
    approved: bool
    summary: str


def dispatch(state: BriefState) -> list:
    """Send로 도시마다 city_flow를 흩뿌린다. 모두 동시에 돈다."""
    return [Send("city_flow", {"city": c, "reports": []}) for c in state["cities"]]


def approval(state: BriefState) -> dict:
    """발송 전 멈추고 사람의 승인을 받는다. interrupt가 그래프를 여기서 멈춘다."""
    warned = [r["city"] for r in state["reports"] if r.get("warn")]
    ok = interrupt({"질문": "브리핑을 발송할까요?", "주의_도시": warned})
    return {"approved": bool(ok)}


def after_approval(state: BriefState) -> str:
    """승인 결과로 갈래를 정한다. 거절이면 발송을 건너뛴다."""
    if not state["approved"]:
        return "skipped"
    return "summarize_alert" if any(r.get("warn") for r in state["reports"]) else "summarize_normal"


async def _summarize(system: str, reports: list) -> str:
    return await acomplete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": _as_text(reports)},
        ]
    )


async def summarize_alert(state: BriefState) -> dict:
    return {"summary": await _summarize(ALERT_SYSTEM, state["reports"])}


async def summarize_normal(state: BriefState) -> dict:
    return {"summary": await _summarize(NORMAL_SYSTEM, state["reports"])}


def skipped(state: BriefState) -> dict:
    return {"summary": "(사용자가 발송을 취소했습니다)"}


def build_briefing_graph():
    """병렬·서브그래프·재시도·사람 개입을 한 그래프에 엮는다."""
    graph = StateGraph(BriefState)
    graph.add_node("city_flow", CITY_FLOW)              # 서브그래프를 노드로
    graph.add_node("approval", approval)
    graph.add_node("summarize_alert", summarize_alert)
    graph.add_node("summarize_normal", summarize_normal)
    graph.add_node("skipped", skipped)
    graph.add_conditional_edges(START, dispatch, ["city_flow"])  # Send fan-out
    graph.add_edge("city_flow", "approval")                      # 모두 끝나면 fan-in
    graph.add_conditional_edges(
        "approval",
        after_approval,
        {
            "summarize_alert": "summarize_alert",
            "summarize_normal": "summarize_normal",
            "skipped": "skipped",
        },
    )
    graph.add_edge("summarize_alert", END)
    graph.add_edge("summarize_normal", END)
    graph.add_edge("skipped", END)
    return graph.compile(checkpointer=MemorySaver())  # interrupt에는 체크포인터가 필요


BRIEFING = build_briefing_graph()


async def run(cities: list[str], approve: bool = True) -> dict:
    """병렬로 모으고, 승인에서 멈췄다가, 사람의 결정으로 재개한다."""
    config = {"configurable": {"thread_id": "brief"}}
    initial = {"cities": cities, "reports": [], "approved": False, "summary": ""}
    out = await BRIEFING.ainvoke(initial, config)
    print("병렬로 수집한 보고:")
    print(_as_text(out["reports"]))
    if "__interrupt__" in out:
        print(f"\n[중단] 승인 요청: {out['__interrupt__'][0].value}")
        print(f"[사람] {'승인' if approve else '거절'} → 재개")
        out = await BRIEFING.ainvoke(Command(resume=approve), config)
    print(f"\n브리핑: {out['summary']}")
    return out


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("그래프 구조 (LangGraph가 그린 mermaid):")
    print(BRIEFING.get_graph().draw_mermaid())
    print("\n=== 병렬 수집 → 사람 승인 → 발송 ===")
    asyncio.run(run(["Seoul", "Nowhereville123", "Tokyo"], approve=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
