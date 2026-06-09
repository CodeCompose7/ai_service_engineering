"""lec02 — 단일 도구 에이전트.

에이전트는 모델 + 도구 + 제어 루프다. lec01에서 function calling 한 바퀴를 봤다면, 여기서는
도구 하나로 한 작업을 끝까지 해내는 에이전트를 만든다. 모델이 도구를 한 번이 아니라 필요한
만큼 반복해서 부르고, 더 부를 게 없으면 스스로 마무리한다. lec01 데모는 질문마다 도구를 한 번
부르고 끝났지만, 여기서는 루프가 여러 번 돈다.

예: 계산기 도구 하나로 "((12 + 8) × 3) - 5"를 풀려면 calculate를 세 번 연쇄로 부른다
(12+8=20 → 20×3=60 → 60-5=55). 도구가 한 번에 두 수만 다루므로 여러 스텝이 자연히 필요하다.

도구는 lec01의 calculate 하나만 쓰고, 호출도 lec01의 llm을 그대로 경유한다.

실행:
    uv run python src/section3/lec02/agent.py "((12 + 8) 곱하기 3) 빼기 5는?"
"""

import json
import sys

from section3.lec01.llm import call_count, completion, reset_calls, resolve_model
from section3.lec01.tools.calculator import SCHEMA as CALC_SCHEMA
from section3.lec01.tools.calculator import calculate

# 단일 도구 — 계산기 하나만 둔다.
TOOLS = [CALC_SCHEMA]

SYSTEM = (
    "너는 계산기 도구로 수식을 단계별로 푸는 도우미다. calculate는 한 번에 두 수만 "
    "계산하니, 필요하면 여러 번 나눠 부른다. 다 끝나면 최종 결과를 한국어로 말한다."
)


def run_tool(name: str, args: dict):
    """단일 도구를 실행한다. 도구가 하나뿐이라 분기도 짧다."""
    if name == "calculate":
        return calculate(**args)
    raise ValueError(f"모르는 도구: {name}")


def run_agent(task: str, max_steps: int = 10) -> dict:
    """작업이 끝날 때까지 도구를 반복 호출한다. 도구 요청이 없으면 그때가 최종 답이다.

    max_steps는 안전장치다. 모델이 끝없이 도구를 부르는 일을 막는다.
    """
    reset_calls()
    model, kwargs = resolve_model()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    steps = []
    for _ in range(max_steps):
        resp = completion(model, messages, tools=TOOLS, **kwargs)
        msg = resp.choices[0].message
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
            result = run_tool(call.function.name, args)
            steps.append({"args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return {"answer": None, "model": model, "steps": steps, "llm_calls": call_count()}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    tasks = sys.argv[1:] or [
        "((12 + 8) 곱하기 3) 빼기 5는 얼마야?",
        "9 더하기 16은?",
    ]
    for task in tasks:
        print(f"작업: {task}")
        result = run_agent(task)
        for i, step in enumerate(result["steps"], 1):
            a = step["args"]
            print(f"  {i}단계: calculate({a['a']}, {a['b']}, {a['op']}) = {step['result']}")
        print(f"  답 ({result['model']}): {result['answer']}")
        print(f"  도구 {len(result['steps'])}번 호출 · LLM {result['llm_calls']}회\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
