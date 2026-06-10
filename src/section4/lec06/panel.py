"""S4 lec06 — 여러 저지로 채점 (panel.py).

저지가 하나면 그 모델의 편향·맹점이 그대로 점수에 들어간다. 그래서 관점이 다른 저지 여럿을
패널로 두고 모은다. 엄격한 저지, 관대한 저지, 사용자 관점의 저지가 각자 채점한다.

- 의견이 모이면(만장일치) 그 판정은 믿을 만하다.
- 의견이 갈리면 그 답은 애매하다는 신호다. 사람이 들여다볼 후보다.

panel_judge는 EvalHarness의 judge_fn에 그대로 꽂힌다. 저지를 주입식으로 둔 설계가 여기서 빛난다.

실행:
    uv run python src/section4/lec06/panel.py
"""

import asyncio

from section3.lec02.async_llm import acomplete

JUDGES = [
    (
        "엄격",
        "기준을 빠짐없이 충족할 때만 PASS. 어조·완전성까지 깐깐히 본다. "
        "PASS 또는 FAIL만 답하라.",
    ),
    ("관대", "핵심을 담으면 사소한 건 넘어가고 PASS로 본다. PASS 또는 FAIL만 답하라."),
    ("사용자", "사용자가 이 답에 만족할지로 본다. PASS 또는 FAIL만 답하라."),
]


async def _ask(persona: str, question: str, answer: str, criteria: str) -> bool:
    verdict = await acomplete([
        {"role": "system", "content": persona},
        {"role": "user", "content": f"질문: {question}\n기준: {criteria}\n답: {answer}"},
    ])
    return "PASS" in verdict.upper()


def _aggregate(verdicts: dict) -> dict:
    """저지들의 판정을 다수결로 모은다. 일치 수가 곧 확신의 세기다."""
    agreement = sum(verdicts.values())
    return {"verdicts": verdicts, "agreement": agreement, "passed": agreement > len(verdicts) / 2}


async def panel_verdict(question: str, answer: str, criteria: str, judges=JUDGES) -> dict:
    """관점이 다른 저지 여럿에게 채점시켜 모은다."""
    verdicts = {name: await _ask(persona, question, answer, criteria) for name, persona in judges}
    return _aggregate(verdicts)


async def panel_judge(question: str, answer: str, criteria: str) -> bool:
    """EvalHarness에 꽂는 judge_fn. 패널 다수결을 bool로 돌려준다."""
    return (await panel_verdict(question, answer, criteria))["passed"]


QUESTION = "환불 되나요?"
CRITERIA = "환불 가능 여부를 정확히 답하고 친절한 어조로 안내한다"
ANSWERS = [
    "환불 됨.",
    "7일 이내 환불 가능합니다.",
    "네 고객님, 환불은 결제 후 7일 이내에 가능하니 편히 신청해 주세요.",
]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("=== 멀티 저지 패널 (엄격·관대·사용자) ===")
    print(f"질문: {QUESTION}\n기준: {CRITERIA}\n")
    for answer in ANSWERS:
        result = asyncio.run(panel_verdict(QUESTION, answer, CRITERIA))
        marks = {name: ("PASS" if ok else "FAIL") for name, ok in result["verdicts"].items()}
        final = "PASS" if result["passed"] else "FAIL"
        print(f"답: {answer}")
        print(f"  저지: {marks} → {result['agreement']}/3 다수결 {final}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
