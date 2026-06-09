"""lec07 — 자기수정 에이전트 (reflection).

한 번에 잘 쓰기는 어렵다. 사람도 초안을 쓰고, 다시 읽고, 고친다. 자기수정 에이전트는 그 과정을
모델이 스스로 한다. 초안을 만들고, 자기 출력을 비평하고, 비평을 반영해 고친다. 충분히 좋아지거나
정해진 횟수에 이르면 멈춘다.

흐름: generate(초안) → critique(비평) → revise(수정) → 반복. LangGraph 없이 우리 async 루프로
짠다. 호출은 lec02 async_llm을 쓴다.

실행:
    uv run python src/section3/lec07/reflection.py
"""

import asyncio

from section3.lec02.async_llm import acomplete

WRITER = "주어진 과제를 푼다. 파이썬 코드를 요청하면 코드만 낸다."
CRITIC = (
    "초안의 약점을 두세 가지 짚는다. 에러 처리·엣지 케이스·효율·가독성을 본다. "
    "더 고칠 게 없으면 첫 줄에 OK라고만 답한다."
)
REVISER = "비평을 반영해 초안을 고친다. 설명 없이 고친 결과만 낸다."


def _msg(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _is_satisfied(critique: str) -> bool:
    """비평이 OK로 시작하면 더 고칠 게 없다는 신호다."""
    return critique.strip().upper().startswith("OK")


async def run(task: str, max_rounds: int = 2) -> dict:
    """초안을 만들고, 비평과 수정을 반복하며 다듬는다."""
    draft = await acomplete(_msg(WRITER, task))
    trace = [("초안", draft)]
    for i in range(max_rounds):
        critique = await acomplete(_msg(CRITIC, f"과제: {task}\n초안:\n{draft}"))
        trace.append((f"{i + 1}차 비평", critique))
        if _is_satisfied(critique):
            break
        draft = await acomplete(_msg(REVISER, f"과제: {task}\n초안:\n{draft}\n비평:\n{critique}"))
        trace.append((f"{i + 1}차 수정", draft))
    return {"final": draft, "trace": trace}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    task = "파이썬으로 두 정수의 최대공약수를 구하는 함수를 작성해줘."
    result = asyncio.run(run(task))
    print(f"과제: {task}\n")
    for label, text in result["trace"]:
        print(f"=== {label} ===")
        print(text.strip()[:300])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
