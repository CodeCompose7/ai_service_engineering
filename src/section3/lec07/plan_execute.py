"""lec07 — 계획 수립 에이전트 (plan-and-execute).

지금까지의 에이전트는 반응형이었다. 모델이 매 스텝 다음 행동을 즉흥으로 정했다(lec02~03). 계획
수립은 다르다. 먼저 전체 계획을 세우고, 그 계획대로 단계를 차례로 실행한다. 길이 복잡할수록 즉흥보다
선계획이 흐트러지지 않는다.

흐름: 과제 → 계획(단계 목록) → 단계마다 실행 → 종합. LangGraph 없이 우리 async 루프로 짠다. 곧
패턴이지 프레임워크가 아니다. 호출은 lec02 async_llm을 쓴다.

실행:
    uv run python src/section3/lec07/plan_execute.py
"""

import asyncio
import re

from section3.lec02.async_llm import acomplete

PLANNER = "과제를 3~4개의 짧은 단계로 쪼갠다. 한 줄에 한 단계만, 번호 없이 쓴다."
EXECUTOR = "계획의 한 단계를 수행한다. 앞 결과를 참고해 이번 단계만 두세 문장으로 처리한다."
SYNTH = "단계 결과들을 매끄러운 한 편의 글로 합친다. 군더더기 없이 쓴다."


def _msg(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_plan(text: str) -> list[str]:
    """계획 텍스트를 단계 목록으로 자른다. 빈 줄을 버리고 앞머리 불릿·번호만 떼낸다."""
    steps = []
    for line in text.splitlines():
        cleaned = re.sub(r"^[\s\-•*]+", "", line)   # 앞 불릿·공백
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned)  # 앞 '1.' '1)'
        if cleaned.strip():
            steps.append(cleaned.strip())
    return steps


async def make_plan(task: str) -> list[str]:
    """과제를 단계 목록으로 쪼갠다."""
    return _parse_plan(await acomplete(_msg(PLANNER, task)))


async def run(task: str) -> dict:
    """계획을 세우고, 단계마다 실행한 뒤, 결과를 종합한다."""
    steps = await make_plan(task)
    results: list[str] = []
    for step in steps:
        done = "\n".join(f"- {s}: {r}" for s, r in zip(steps, results, strict=False))
        prompt = f"과제: {task}\n지금까지:\n{done or '(아직 없음)'}\n이번 단계: {step}"
        out = await acomplete(_msg(EXECUTOR, prompt))
        results.append(out.replace("\n", " ").strip())
    joined = "\n".join(
        f"{i}. {s}\n   {r}" for i, (s, r) in enumerate(zip(steps, results, strict=True), 1)
    )
    final = await acomplete(_msg(SYNTH, f"과제: {task}\n\n{joined}"))
    return {"plan": steps, "results": results, "final": final}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    task = "초보자에게 RAG가 무엇인지 설명하는 짧은 글을 써줘."
    result = asyncio.run(run(task))
    print(f"과제: {task}\n")
    print("세운 계획:")
    for i, step in enumerate(result["plan"], 1):
        print(f"  {i}. {step}")
    print(f"\n종합한 글:\n{result['final']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
