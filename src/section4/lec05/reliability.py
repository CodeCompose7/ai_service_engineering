"""S4 lec05 — 운영 신뢰성 (reliability.py).

"동작하는" 에이전트를 "출하 가능한" 시스템으로 만들려면 비용·한계·실패를 견뎌야 한다. 모델 호출
둘레에 운영 층을 두른다.

- 비용·토큰 예산: 토큰을 누적해 한도를 넘으면 막는다. 폭주를 막는 안전판이다.
- 재시도·백오프: 일시적 실패(레이트리밋 429·타임아웃)는 잠깐 쉬었다 다시 시도한다. 쉬는 간격을
  지수로 늘려(백오프) 서버를 더 밀어붙이지 않는다.
- 폴백 체인: 한 모델이 안 되면 다음 모델로 넘어간다.
- 타임아웃: 제한 시간을 넘으면 끊는다. 무한정 기다리지 않는다.

여기서는 패턴을 손으로 짜 보인다. 실전에서는 이 call이 LiteLLM 호출이고, LiteLLM이 num_retries·
fallbacks·timeout을 내장 지원한다. 직접 짜 보면 그 내장 기능이 무엇을 하는지 또렷해진다.

실행:
    uv run python src/section4/lec05/reliability.py
"""

import asyncio


class BudgetError(Exception):
    """토큰 예산을 넘었을 때."""


class RateLimitError(Exception):
    """레이트리밋(429)을 모사한다. 실전에서는 litellm.RateLimitError."""


class Budget:
    """토큰 예산. 쓴 만큼 누적하고 한도를 넘으면 막는다."""

    def __init__(self, limit: int):
        self.limit = limit
        self.spent = 0

    def charge(self, tokens: int) -> None:
        if self.spent + tokens > self.limit:
            raise BudgetError(f"예산 초과: {self.spent} + {tokens} > {self.limit}")
        self.spent += tokens

    def remaining(self) -> int:
        return self.limit - self.spent


RETRYABLE = (RateLimitError, TimeoutError)


async def with_retry(call, max_attempts=4, base_delay=0.05, on_retry=None):
    """일시적 실패는 지수 백오프로 다시 시도한다. 마지막 시도까지 실패하면 그대로 올린다."""
    for attempt in range(max_attempts):
        try:
            return await call()
        except RETRYABLE as exc:
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt)
            if on_retry:
                on_retry(attempt + 1, delay, exc)
            await asyncio.sleep(delay)
    return None


async def with_fallback(calls, on_fallback=None):
    """앞 호출이 실패하면 다음으로 넘어간다. 모두 실패하면 마지막 예외를 올린다."""
    last_exc = None
    for index, call in enumerate(calls):
        try:
            return await call()
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 다음 후보로 넘긴다
            last_exc = exc
            if on_fallback:
                on_fallback(index, exc)
    raise last_exc


async def with_timeout(call, seconds: float):
    """제한 시간을 넘으면 TimeoutError로 끊는다."""
    return await asyncio.wait_for(call(), timeout=seconds)


def _demo_budget() -> None:
    print("=== 비용·토큰 예산 (한도 1000) ===")
    budget = Budget(limit=1000)
    for cost in [400, 400, 400]:
        try:
            budget.charge(cost)
            print(f"  +{cost} 토큰 → 남은 예산 {budget.remaining()}")
        except BudgetError as exc:
            print(f"  +{cost} 토큰 → {exc}")


def _demo_retry() -> None:
    print("\n=== 재시도·백오프 (429 두 번 뒤 성공) ===")
    state = {"n": 0}

    async def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise RateLimitError("429 Too Many Requests")
        return "성공"

    def log(attempt, delay, exc):
        print(f"  {attempt}번째 실패({exc}) → {delay:.2f}s 대기 후 재시도")

    result = asyncio.run(with_retry(flaky, on_retry=log))
    print(f"  결과: {result} (총 {state['n']}회 시도)")


def _demo_fallback() -> None:
    print("\n=== 폴백 체인 (앞 모델 실패 → 다음) ===")

    async def model_a():
        raise RateLimitError("모델 A 과부하")

    async def model_b():
        return "모델 B 응답"

    def log(index, exc):
        print(f"  후보 {index} 실패({exc}) → 다음으로")

    result = asyncio.run(with_fallback([model_a, model_b], on_fallback=log))
    print(f"  결과: {result}")


def _demo_timeout() -> None:
    print("\n=== 타임아웃 (0.1s 한도) ===")

    async def slow():
        await asyncio.sleep(1)
        return "느린 응답"

    try:
        asyncio.run(with_timeout(slow, seconds=0.1))
    except TimeoutError:
        print("  0.1s 초과 → TimeoutError로 끊음")


def main() -> int:
    _demo_budget()
    _demo_retry()
    _demo_fallback()
    _demo_timeout()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
