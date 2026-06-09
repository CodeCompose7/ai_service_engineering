"""lec06 — LangGraph 실전 (자동화 그래프).

lec05는 모델이 매 스텝을 정하는 에이전트 루프였다. 여기서는 우리가 흐름을 설계한다. 분기와
루프를 노드·엣지로 직접 짜고, 도구는 정해진 자리에서 자동으로 불린다. 그래프가 에이전트가
아니라 워크플로 엔진이 된다.

예: 도시 목록의 날씨 브리핑을 자동으로 만든다.
- 루프: 도시를 하나씩 처리한다(index 카운터). 도시마다 geocode → get_weather를 자동 호출한다.
- 분기: 한 조건 엣지가 셋을 가른다. 도시가 남았으면 fetch_one으로 되돌아가고(루프), 끝났으면
  비·눈 같은 주의 도시가 있는지로 갈래를 나눠 알림형/일반형 요약으로 간다.

도구는 lec03, 요약 호출은 lec02 async_llm을 쓴다.

실행:
    uv run python src/section3/lec06/graph.py
"""

import asyncio
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from section3.lec02.async_llm import acomplete
from section3.lec03.tools.errors import ToolError
from section3.lec03.tools.geocode import geocode
from section3.lec03.tools.weather import get_weather

WARN_KEYWORDS = ("비", "눈", "소나기", "뇌우", "이슬비")
ALERT_SYSTEM = (
    "날씨 보고를 한국어 두세 문장으로 브리핑하되, 비·눈 등 주의 도시를 먼저 짚어 알린다."
)
NORMAL_SYSTEM = "날씨 보고를 한국어 두세 문장으로 담백하게 브리핑한다."


class State(TypedDict):
    cities: list[str]                       # 처리할 도시 목록 (입력)
    index: int                              # 진행 위치 (루프 카운터)
    reports: Annotated[list, operator.add]  # 도시별 결과를 누적
    summary: str                            # 마지막 요약 (마지막 값으로 덮음)


async def fetch_one(state: State) -> dict:
    """현재 도시 하나의 날씨를 가져와 보고에 더하고, index를 한 칸 민다."""
    city = state["cities"][state["index"]]
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
    return {"reports": [report], "index": state["index"] + 1}


def route(state: State) -> str:
    """조건 엣지 — 도시가 남았으면 루프, 끝났으면 주의 유무로 갈래를 나눈다."""
    if state["index"] < len(state["cities"]):
        return "fetch_one"                      # 루프: 다음 도시로
    if any(r.get("warn") for r in state["reports"]):
        return "summarize_alert"                # 갈래: 주의 도시 있음
    return "summarize_normal"                   # 갈래: 모두 무난


def _as_text(reports: list) -> str:
    lines = []
    for r in reports:
        if "error" in r:
            lines.append(f"{r['city']}: 조회 실패")
        else:
            mark = " (주의)" if r["warn"] else ""
            lines.append(f"{r['city']}: {r['temp_c']}도, {r['condition']}{mark}")
    return "\n".join(lines)


async def summarize_alert(state: State) -> dict:
    """주의 도시가 있을 때 — 비·눈 도시를 강조해 브리핑한다."""
    summary = await acomplete(
        [
            {"role": "system", "content": ALERT_SYSTEM},
            {"role": "user", "content": _as_text(state["reports"])},
        ]
    )
    return {"summary": summary}


async def summarize_normal(state: State) -> dict:
    """모두 무난할 때 — 담백하게 브리핑한다."""
    summary = await acomplete(
        [
            {"role": "system", "content": NORMAL_SYSTEM},
            {"role": "user", "content": _as_text(state["reports"])},
        ]
    )
    return {"summary": summary}


def build_graph():
    """루프(fetch_one 되돌이)와 분기(요약 갈래)를 가진 자동화 그래프를 짠다."""
    graph = StateGraph(State)
    graph.add_node("fetch_one", fetch_one)
    graph.add_node("summarize_alert", summarize_alert)
    graph.add_node("summarize_normal", summarize_normal)
    graph.add_edge(START, "fetch_one")
    graph.add_conditional_edges(
        "fetch_one",
        route,
        {
            "fetch_one": "fetch_one",
            "summarize_alert": "summarize_alert",
            "summarize_normal": "summarize_normal",
        },
    )
    graph.add_edge("summarize_alert", END)
    graph.add_edge("summarize_normal", END)
    return graph.compile()


APP = build_graph()


async def run(cities: list[str]) -> dict:
    """도시 목록을 받아, 노드별로 도는 과정을 보이며 브리핑까지 만든다. 한 번만 실행한다."""
    initial = {"cities": cities, "index": 0, "reports": [], "summary": ""}
    reports, summary = [], ""
    async for update in APP.astream(initial, stream_mode="updates"):
        for node, delta in update.items():
            if node == "fetch_one":
                reports += delta["reports"]
                print(f"  [fetch_one] {delta['reports'][0]['city']} 처리 (index→{delta['index']})")
            else:
                summary = delta["summary"]
                print(f"  [{node}] 갈래 선택")
    return {"reports": reports, "summary": summary}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("그래프 구조 (LangGraph가 그린 mermaid):")
    print(APP.get_graph().draw_mermaid())

    cities = ["Seoul", "Tokyo", "London"]
    print(f"\n=== 자동화 실행: {cities} ===")
    state = asyncio.run(run(cities))
    print("\n수집한 보고:")
    print(_as_text(state["reports"]))
    print(f"\n브리핑: {state['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
