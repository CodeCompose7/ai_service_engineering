"""S4 lec05 — 공통 관심사를 호출 층에 붙이기 (compose.py).

하네스를 여럿 만들면(비속어 감지·요약·번역…) 예산 같은 공통 관심사를 다 더하고 싶어진다.
클래스마다 찾아가 박거나 상속으로 끌고 가지 않는다. 예산은 '호출'의 관심사이므로, 모두가 지나는
호출 한 곳을 감싸고, 그것을 하네스에 주입한다(의존성 주입).

핵심: 하네스는 llm을 '받는다'. acomplete를 직접 부르지 않는다. 그래서 예산을 입힌 llm을 넣으면
모든 하네스가 같은 예산을 공유한다. 한 곳만 감싸고, 클래스는 손대지 않는다.

실행:
    uv run python src/section4/lec05/compose.py
"""

import asyncio

from section4.lec05.reliability import Budget, BudgetError


async def fake_llm(messages: list[dict]) -> str:
    """결정적인 가짜 모델 호출. 실전에서는 acomplete가 들어갈 자리."""
    return f"[응답] {messages[-1]['content']}"


def _cost(messages: list[dict]) -> int:
    """토큰을 흉내 낸다. 마지막 메시지 글자 수를 비용으로 친다."""
    return len(messages[-1]["content"])


def budgeted(call, budget: Budget):
    """호출을 예산으로 감싼다. 이 한 겹을 모든 하네스가 공유한다."""

    async def wrapped(messages: list[dict]) -> str:
        budget.charge(_cost(messages))
        return await call(messages)

    return wrapped


# 하네스들은 llm을 주입받는다. 메서드 이름이 달라도 다 llm(messages)로 부른다.
class SummarizeHarness:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, text: str) -> str:
        return await self.llm([{"role": "user", "content": f"요약: {text}"}])


class TranslateHarness:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, text: str) -> str:
        return await self.llm([{"role": "user", "content": f"번역: {text}"}])


def main() -> int:
    # 예산을 호출에 한 번 두르고, 두 하네스에 같은 llm을 주입한다.
    budget = Budget(limit=40)
    llm = budgeted(fake_llm, budget)
    summarize = SummarizeHarness(llm)
    translate = TranslateHarness(llm)

    print("=== 두 하네스가 한 예산을 공유 (한도 40) ===")
    work = [
        (summarize, "오늘 회의"),
        (translate, "good"),
        (summarize, "내일 일정"),
        (translate, "bye"),
        (summarize, "마지막 요청"),
    ]
    for harness, text in work:
        name = type(harness).__name__
        try:
            asyncio.run(harness.run(text))
            print(f"  {name}: 성공 → 남은 예산 {budget.remaining()}")
        except BudgetError as exc:
            print(f"  {name}: 거부 ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
