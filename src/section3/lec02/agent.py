"""lec02 — 단일 도구 에이전트.

에이전트는 모델 + 도구 + 제어 루프다. lec01에서 function calling 한 바퀴를 봤다면, 여기서는
도구 하나로 한 작업을 끝까지 해내는 에이전트를 만든다. 모델이 도구를 한 번이 아니라 필요한
만큼 반복해서 부르고, 더 부를 게 없으면 스스로 마무리한다.

핵심은 루프가 도구와 무관하다는 것이다. run_agent에 도구만 바꿔 끼우면 다른 에이전트가 된다.
여기서는 같은 루프로 두 에이전트를 돌린다.
- 계산기 에이전트: calculate 하나로 여러 단계 수식을 푼다. (12+8=20 → 20×3=60 → 60-5=55)
- 위키 검색 에이전트: search_wikipedia 하나로 여러 주제를 차례로 찾아 답한다.

도구와 호출(resolve_model·completion·카운터)은 lec01 것을 그대로 쓴다.

실행:
    uv run python src/section3/lec02/agent.py
"""

import json

from section3.lec01.llm import call_count, completion, reset_calls, resolve_model
from section3.lec01.tools.calculator import SCHEMA as CALC_SCHEMA
from section3.lec01.tools.calculator import calculate
from section3.lec01.tools.search_wikipedia import SCHEMA as WIKI_SCHEMA
from section3.lec01.tools.search_wikipedia import search_wikipedia


def run_agent(task: str, tools: list, dispatch, system: str, max_steps: int = 10) -> dict:
    """주어진 도구로 작업을 끝까지 수행한다. 도구 요청이 멈추면 그때가 최종 답이다.

    tools는 모델에 줄 스키마 목록, dispatch는 이름·인자로 도구를 실행하는 함수다. 도구를
    바꿔도 이 루프는 그대로다. max_steps는 끝없는 반복을 막는 안전장치다.
    """
    reset_calls()
    model, kwargs = resolve_model()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    steps = []
    for _ in range(max_steps):
        msg = completion(model, messages, tools=tools, **kwargs).choices[0].message
        messages.append(msg.model_dump())
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "model": model,
                "steps": steps,
                "llm_calls": call_count(),
            }
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = dispatch(call.function.name, args)
            steps.append({"name": call.function.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return {"answer": None, "model": model, "steps": steps, "llm_calls": call_count()}


# --- 계산기 에이전트 — 도구 하나로 다단계 수식 ---
CALC_SYSTEM = (
    "너는 계산기 도구로 수식을 단계별로 푸는 도우미다. calculate는 한 번에 두 수만 "
    "계산하니, 필요하면 여러 번 나눠 부른다. 다 끝나면 최종 결과를 한국어로 말한다."
)


def _calc_dispatch(_name: str, args: dict):  # 단일 도구라 이름은 보지 않는다
    return calculate(**args)


def calc_agent(task: str) -> dict:
    return run_agent(task, [CALC_SCHEMA], _calc_dispatch, CALC_SYSTEM)


# --- 위키 검색 에이전트 — 도구 하나로 여러 주제 검색 ---
WIKI_SYSTEM = (
    "너는 위키백과 검색 도구로 사실을 알아보는 도우미다. 여러 주제가 나오면 주제마다 "
    "search_wikipedia를 따로 부른다. 검색 결과만 근거로 한국어로 답하고 출처를 밝힌다."
)


def _wiki_dispatch(_name: str, args: dict):  # 단일 도구라 이름은 보지 않는다
    return search_wikipedia(**args)


def wiki_agent(task: str) -> dict:
    return run_agent(task, [WIKI_SCHEMA], _wiki_dispatch, WIKI_SYSTEM)


def _show(task: str, result: dict) -> None:
    print(f"작업: {task}")
    for i, step in enumerate(result["steps"], 1):
        shown = ", ".join(f"{k}={v}" for k, v in step["args"].items())
        out = str(step["result"]).replace("\n", " ")[:54]
        print(f"  {i}단계: {step['name']}({shown}) → {out}")
    print(f"  답 ({result['model']}): {str(result['answer']).replace(chr(10), ' ')[:90]}")
    print(f"  도구 {len(result['steps'])}번 · LLM {result['llm_calls']}회\n")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    print("=== 계산기 에이전트 (단일 도구: calculate) ===")
    for task in ["((12 + 8) 곱하기 3) 빼기 5는 얼마야?", "9 더하기 16은?"]:
        _show(task, calc_agent(task))

    print("=== 위키 검색 에이전트 (단일 도구: search_wikipedia) ===")
    for task in [
        "에펠탑과 도쿄 타워는 각각 언제 지어졌나요?",
        "만리장성과 콜로세움은 각각 어느 나라에 있나요?",
    ]:
        _show(task, wiki_agent(task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
