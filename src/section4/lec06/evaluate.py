"""S4 lec06 — 평가·검증 (evaluate.py).

"좋아진 것 같다"는 느낌으로는 못 고친다. 품질을 숫자로 재야 개선이 보인다. 평가 하네스는
테스트셋에 에이전트를 돌리고, 각 답을 LLM-as-judge로 채점해 품질 점수를 낸다.

- 테스트셋: 질문 + 기준(좋은 답이 갖춰야 할 것)의 목록.
- LLM-as-judge: 답이 기준을 충족하는지 모델로 판정한다(PASS/FAIL).
- 품질 점수: 통과율로 모은다.
- 개선 로그: 버전 전후 점수를 비교한다. 한계 분석: 어떤 케이스가 실패했는지 본다.

실행:
    uv run python src/section4/lec06/evaluate.py
"""

import asyncio

from section3.lec02.async_llm import acomplete

# 제품 지식. 개선 에이전트만 이걸 근거로 받는다.
KNOWLEDGE = (
    "Pro 플랜은 팀 협업 기능을 포함한다. 환불은 결제 후 7일 이내에 가능하다. "
    "데이터는 한국 리전 서버에 저장된다."
)
WEAK_SYSTEM = "너는 고객 지원 도우미다. 질문에 친절하게 답한다."
STRONG_SYSTEM = f"{WEAK_SYSTEM} 다음 제품 정보를 근거로 답한다: {KNOWLEDGE}"

# 테스트셋 — 질문과, 좋은 답이 갖춰야 할 기준.
TESTSET = [
    {"q": "환불 되나요?", "criteria": "결제 후 7일 이내 환불 가능을 안내한다"},
    {"q": "팀으로 같이 쓸 수 있나요?", "criteria": "Pro 플랜의 팀 협업 기능을 안내한다"},
    {"q": "데이터는 어디에 저장되나요?", "criteria": "한국 리전 서버 저장을 안내한다"},
]

JUDGE = "답이 기준을 충족하면 PASS, 아니면 FAIL이라고만 답하라."


async def judge(question: str, answer: str, criteria: str) -> bool:
    """답이 기준을 충족하는지 모델로 판정한다. 사람 대신 모델이 채점한다."""
    verdict = await acomplete([
        {"role": "system", "content": JUDGE},
        {"role": "user", "content": f"질문: {question}\n기준: {criteria}\n답: {answer}"},
    ])
    return "PASS" in verdict.upper()


def _score(results: list[dict]) -> float:
    """통과율을 낸다. 통과 수 ÷ 전체."""
    return sum(r["passed"] for r in results) / len(results) if results else 0.0


class EvalHarness:
    """테스트셋에 에이전트를 돌리고 LLM-judge로 채점하는 평가 하네스."""

    def __init__(self, testset, judge_fn=judge):
        self.testset = testset
        self.judge = judge_fn

    async def run(self, answer_fn) -> dict:
        """answer_fn(question) → answer를 테스트셋에 돌려 채점한다."""
        results = []
        for case in self.testset:
            answer = await answer_fn(case["q"])
            passed = await self.judge(case["q"], answer, case["criteria"])
            results.append({"q": case["q"], "passed": passed})
        return {"score": _score(results), "results": results}


def _agent(system: str):
    """시스템 프롬프트로 답하는 에이전트(answer_fn)를 만든다."""

    async def answer_fn(question: str) -> str:
        return await acomplete([
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ])

    return answer_fn


def _report(label: str, result: dict) -> None:
    print(f"=== {label}: 품질 {result['score']:.0%} ===")
    for case in result["results"]:
        mark = "PASS" if case["passed"] else "FAIL"
        print(f"  [{mark}] {case['q']}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    harness = EvalHarness(TESTSET)

    weak = asyncio.run(harness.run(_agent(WEAK_SYSTEM)))
    strong = asyncio.run(harness.run(_agent(STRONG_SYSTEM)))

    _report("약한 에이전트 (지식 없음)", weak)
    _report("개선 에이전트 (지식 주입)", strong)

    print(f"\n개선 로그: {weak['score']:.0%} → {strong['score']:.0%}")
    failed = [c["q"] for c in weak["results"] if not c["passed"]]
    print(f"한계 분석(약한 버전 실패): {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
