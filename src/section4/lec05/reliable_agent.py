"""S4 lec05 — 운영 신뢰성을 끼운 하네스 (reliable_agent.py).

reliability.py가 패턴을 따로 보였다면, 여기서는 모델 호출 둘레에 그것들을 한 흐름으로 두른다.

ask 한 번에:
    예산 차감 → 폴백 체인을 돈다(각 후보는 재시도 + 타임아웃) → 첫 성공을 돌려준다
    예산을 넘으면 모델을 부르지도 않고 거부한다.

이것이 운영 층이다. lec02~04의 하네스가 모델을 부르던 그 자리를, 비용·실패·지연에 견디게 감싼다.

실행:
    uv run python src/section4/lec05/reliable_agent.py
"""

import asyncio

import litellm

from section3.lec02.async_llm import acomplete
from section4.lec05.reliability import (
    Budget,
    BudgetError,
    RateLimitError,
    with_retry,
    with_timeout,
)

COUNT_MODEL = "gemini/gemini-2.5-flash"


def _count(messages: list[dict]) -> int:
    return litellm.token_counter(model=COUNT_MODEL, messages=messages)


class ReliableAgent:
    """모델 호출을 예산·재시도·폴백·타임아웃으로 감싸는 하네스."""

    def __init__(self, models, budget: Budget, retries=2, timeout=15.0):
        self.models = models  # [(이름, async fn(messages))] 폴백 순서대로
        self.budget = budget
        self.retries = retries
        self.timeout = timeout
        self.trace: list[str] = []

    async def ask(self, messages: list[dict]) -> dict:
        """오케스트레이터: 예산 게이트 → 폴백 체인."""
        self.trace = []
        if not self._charge_budget(messages):
            return {"reply": "예산을 초과해 요청을 거부합니다.", "trace": self.trace}
        return await self._try_chain(messages)

    def _charge_budget(self, messages) -> bool:
        """토큰을 추정해 예산을 차감한다. 넘으면 모델을 부르지 않으려 False를 돌려준다."""
        tokens = _count(messages)
        try:
            self.budget.charge(tokens)
        except BudgetError as exc:
            self.trace.append(f"예산 초과 → 거부 ({exc})")
            return False
        self.trace.append(f"예산 {tokens}토큰 차감 (남은 {self.budget.remaining()})")
        return True

    async def _try_chain(self, messages) -> dict:
        """폴백 체인을 돌며 첫 성공을 돌려준다. 모두 실패하면 거부한다."""
        for name, fn in self.models:
            try:
                result = await self._call_one(name, fn, messages)
                self.trace.append(f"{name} 성공")
                return {"reply": result, "trace": self.trace}
            except Exception as exc:  # noqa: BLE001 - 어떤 실패든 다음 후보로
                self.trace.append(f"{name} 실패 → 폴백 ({exc})")
        self.trace.append("모든 후보 실패")
        return {"reply": "일시적으로 응답할 수 없습니다.", "trace": self.trace}

    async def _call_one(self, name, fn, messages):
        """한 후보를 재시도와 타임아웃으로 감싸 부른다."""

        def on_retry(attempt, delay, exc):
            self.trace.append(f"{name} 재시도 {attempt} ({delay:.2f}s, {exc})")

        return await with_timeout(
            lambda: with_retry(lambda: fn(messages), max_attempts=self.retries, on_retry=on_retry),
            self.timeout,
        )


# --- 데모용 모델 후보 ---
async def real_model(messages: list[dict]) -> str:
    """실제 모델(LiteLLM 경유)."""
    return (await acomplete(messages)).strip()


async def flaky_model(messages: list[dict]) -> str:
    """늘 과부하인 모델(레이트리밋 모사)."""
    raise RateLimitError("과부하 429")


def _run(label: str, agent: ReliableAgent, messages: list[dict]) -> None:
    result = asyncio.run(agent.ask(messages))
    print(f"=== {label} ===")
    print(f"  답: {result['reply'][:80]}")
    print(f"  트레이스: {result['trace']}\n")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    messages = [{"role": "user", "content": "RAG가 무엇인지 한 문장으로 설명해줘"}]

    normal = ReliableAgent([("주모델", real_model)], Budget(10000))
    _run("정상 (예산 충분, 1차 성공)", normal, messages)
    _run(
        "1차 다운 → 폴백",
        ReliableAgent([("주모델", flaky_model), ("보조모델", real_model)], Budget(10000)),
        messages,
    )
    _run("예산 초과 (한도 5토큰)", ReliableAgent([("주모델", real_model)], Budget(5)), messages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
