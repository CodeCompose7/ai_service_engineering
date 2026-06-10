"""S4 lec02 — 내용 검열 하네스 (harness3.py).

욕설·비속어는 패턴(regex)으로 다 잡기 어렵다. 띄어쓰기·자모 분리·철자 변형이 끝이 없어서, 차단
목록은 늘 새는 구멍이 생긴다. 그래서 의미로 판단하는 방법을 쓴다.

여기서는 모델에게 검열을 맡긴다(LLM-as-judge). 모델이 뜻을 보고 욕설인지 가른다. regex 차단
목록과 나란히 돌려, regex가 놓치는 변형을 LLM이 잡는 것을 보인다.

판단을 비-regex로 하는 다른 방법:
- moderation API: OpenAI /moderations, litellm.moderation 등 전용 엔드포인트.
- 전용 분류기: Detoxify 같은 독성 분류 모델.
- 임베딩 유사도: 시드 욕설과 임베딩 거리를 재서 가까우면 차단 (S2 임베더 재사용).
여기서는 가장 일반적이고 우리 스택에 바로 붙는 LLM 검열을 쓴다.

실행:
    uv run python src/section4/lec02/harness3.py
"""

import asyncio

from section3.lec02.async_llm import acomplete
from section4.lec02.harness import GuardError

MODERATOR = (
    "다음 텍스트에 욕설·비속어·모욕·혐오 표현이 있으면 BLOCK, 없으면 OK라고만 답해라. "
    "띄어쓰기나 철자를 비틀어 숨긴 욕설도 BLOCK으로 본다. 한 단어로만 답해라."
)
RESPONDER = "한국어로 짧고 친절하게 답한다."

# 순진한 차단 목록. 변형 앞에서는 늘 샌다.
REGEX_DENYLIST = ("쓰레기", "멍청이", "바보")


def regex_flag(text: str) -> bool:
    """차단 목록에 든 말이 그대로 있으면 잡는다. 띄어쓰기·변형이면 놓친다."""
    return any(bad in text for bad in REGEX_DENYLIST)


async def llm_moderate(text: str) -> bool:
    """모델에게 욕설 여부를 묻는다. 뜻으로 판단하므로 변형에도 강하다."""
    verdict = await acomplete(
        [{"role": "system", "content": MODERATOR}, {"role": "user", "content": text}]
    )
    return "BLOCK" in verdict.upper()


class ModeratedHarness:
    """입력과 출력을 LLM 검열로 거르는 하네스. 욕설은 모델에도 사용자에도 닿지 못한다."""

    def __init__(self, model_system: str = RESPONDER):
        self.model_system = model_system
        self.trace: list[str] = []

    async def run(self, task: str) -> str:
        """입력 검열 → 응답 → 출력 검열."""
        self.trace = []
        if await llm_moderate(task):
            self.trace.append("입력 검열: 차단")
            raise GuardError("부적절한 표현이 감지되어 차단했습니다")
        self.trace.append("입력 검열: 통과")

        answer = await self._respond(task)

        if await llm_moderate(answer):
            self.trace.append("출력 검열: 차단")
            return "(부적절한 내용이 감지되어 응답을 보류합니다)"
        self.trace.append("출력 검열: 통과")
        return answer

    async def _respond(self, task: str) -> str:
        return await acomplete(
            [{"role": "system", "content": self.model_system}, {"role": "user", "content": task}]
        )


COMPARE_SAMPLES = [
    "오늘 날씨 어때?",
    "야 이 쓰레기야",
    "야 이 쓰 레 기야",
]
RUN_CASES = [
    "좋은 하루 보내는 법 하나만 알려줘",
    "야 이 쓰 레 기야",
]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("=== regex vs LLM 검열 ===")
    for text in COMPARE_SAMPLES:
        rx = "차단" if regex_flag(text) else "통과"
        llm = "차단" if asyncio.run(llm_moderate(text)) else "통과"
        print(f"  {text!r:18} regex={rx} / LLM={llm}")

    print("\n=== 검열 하네스 ===")
    harness = ModeratedHarness()
    for task in RUN_CASES:
        print(f"과제: {task}")
        try:
            print(f"  답: {asyncio.run(harness.run(task))}")
        except GuardError as exc:
            print(f"  차단: {exc}")
        print(f"  트레이스: {harness.trace}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
