"""lec03 — 멀티툴 에이전트 (라우팅).

도구가 여럿일 때 모델이 질문에 맞는 도구를 고른다(라우팅). 위치 도구(geocode·weather·air)와
쇼핑 도구(find_user·orders·detail)를 한 에이전트에 주고, 질문에 따라 알맞은 도구로 간다.

연계: 날씨는 geocode → weather, 주문은 find_user → orders → detail로 이어진다. 앞 결과가 다음
입력이라 순서를 못 바꾼다. 반대로 한 도시의 weather와 air는 서로 독립이라 한 턴에 함께 와서
asyncio.gather로 동시에 실행된다.

호출은 lec02 async_llm을, 도구는 lec03/tools를 쓴다.

실행:
    uv run python src/section3/lec03/agent.py
"""

import asyncio
import json
from dataclasses import asdict

from section3.lec01.llm import resolve_model
from section3.lec02.async_llm import acompletion, call_count, reset_calls
from section3.lec03.tools import TOOLS, run_tool
from section3.lec03.tools.errors import ToolError

SYSTEM = (
    "너는 여러 도구를 쓰는 도우미다. 질문에 맞는 도구를 골라 부른다. 날씨·미세먼지는 먼저 "
    "geocode로 좌표를 얻어 넘기고, 주문 조회는 find_user로 id를 얻어 get_orders·get_order_detail로 "
    "이어 간다. 도구 결과만 근거로 한국어로 답한다."
)


async def _call(name: str, args: dict) -> str:
    """도구를 부르고 결과를 메시지용 JSON 문자열로 만든다.

    도구는 dataclass를 돌려주므로 asdict로 dict로 바꿔 직렬화한다. 도구가 막히면(ToolError)
    에러를 담아, 모델이 그 사실을 보고 답하게 한다.
    """
    try:
        payload = asdict(await run_tool(name, args))
    except ToolError as exc:
        payload = {"error": str(exc)}
    return json.dumps(payload, ensure_ascii=False)


async def run_agent(task: str, max_steps: int = 10) -> dict:
    """질문에 맞는 도구를 골라 부르며 작업을 끝낸다. 한 턴의 도구 호출은 동시에 실행한다."""
    reset_calls()
    model, kwargs = resolve_model()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    trace = []
    for _ in range(max_steps):
        msg = (await acompletion(model, messages, tools=TOOLS, **kwargs)).choices[0].message
        messages.append(msg.model_dump())
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "model": model,
                "trace": trace,
                "llm_calls": call_count(),
            }
        parsed = [json.loads(c.function.arguments) for c in msg.tool_calls]
        # 한 턴의 호출을 동시에 실행하고, 각 결과를 메시지용 JSON으로 받는다.
        contents = await asyncio.gather(
            *[_call(c.function.name, a) for c, a in zip(msg.tool_calls, parsed, strict=True)]
        )
        for call, args, content in zip(msg.tool_calls, parsed, contents, strict=True):
            trace.append({"name": call.function.name, "args": args})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
    return {"answer": None, "model": model, "trace": trace, "llm_calls": call_count()}


def _show(task: str, result: dict) -> None:
    print(f"질문: {task}")
    for step in result["trace"]:
        shown = ", ".join(f"{k}={v}" for k, v in step["args"].items())
        print(f"  → {step['name']}({shown})")
    answer = str(result["answer"]).replace("\n", " ")
    print(f"  답 ({result['model']}): {answer}")
    print(f"  도구 {len(result['trace'])}번 · LLM {result['llm_calls']}회\n")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    for task in [
        "서울 날씨랑 미세먼지 알려줘",
        "alice의 주문 내역 보여줘",
        "철수의 첫 주문 상세 알려줘",
        "도쿄 날씨 어때? 그리고 bob 주문도 알려줘",
    ]:
        _show(task, asyncio.run(run_agent(task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
