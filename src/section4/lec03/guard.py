"""S4 lec03 — 가드레일: 허용 행동 제약·출력 검증·PII (guard.py).

lec02 하네스에서 자리만 잡아 둔 가드레일을 본격적으로 채운다. 세 가지를 본다.

- 허용 행동 제약: 에이전트가 할 수 있는 행동을 목록으로 못박는다. 목록 밖은 막는다.
- 출력 검증: 모델 출력이 우리가 정한 계약(Pydantic 스키마)을 지키는지 본다. 어기면 막는다.
- PII 마스킹: 이메일·전화·주민번호 같은 개인정보를 내보내기 전에 가린다.

출력 검증은 S1의 구조화 출력과 같은 결이다. 모델을 믿지 않고 스키마로 받아 검사한다.

실행:
    uv run python src/section4/lec03/guard.py
"""

import re

from pydantic import BaseModel, Field, ValidationError

from section4.lec02.harness import GuardError

# 허용 행동 제약 — 이 목록 밖의 행동은 막는다.
ALLOWED_ACTIONS = {"lookup", "summarize", "recommend"}

# PII 마스킹 규칙.
PII_RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[이메일]"),
    (re.compile(r"01[016789]-?\d{3,4}-?\d{4}"), "[전화]"),
    (re.compile(r"\d{6}-\d{7}"), "[주민번호]"),
]


def check_action(action: str) -> None:
    """허용 목록에 없는 행동이면 막는다."""
    if action not in ALLOWED_ACTIONS:
        raise GuardError(f"허용되지 않은 행동: {action}")


def redact_pii(text: str) -> str:
    """개인정보를 정규식으로 가린다."""
    for pattern, repl in PII_RULES:
        text = pattern.sub(repl, text)
    return text


class Reply(BaseModel):
    """모델 출력이 지켜야 할 계약. answer는 문자열, confidence는 0~1."""

    answer: str
    confidence: float = Field(ge=0, le=1)


def validate_output(data: dict) -> Reply:
    """출력이 계약을 지키는지 검증한다. 어기면 GuardError로 막는다."""
    try:
        return Reply(**data)
    except ValidationError as exc:
        raise GuardError(f"출력 검증 실패: {exc.error_count()}건") from exc


def main() -> int:
    print("=== 허용 행동 제약 ===")
    for action in ["lookup", "delete_account"]:
        try:
            check_action(action)
            print(f"  {action}: 허용")
        except GuardError as exc:
            print(f"  {action}: 막힘 ({exc})")

    print("\n=== PII 마스킹 ===")
    text = "고객 이메일은 alice@example.com, 전화는 010-1234-5678입니다."
    print(f"  원문:   {text}")
    print(f"  마스킹: {redact_pii(text)}")

    print("\n=== 출력 검증 (Pydantic 계약) ===")
    samples = [
        {"answer": "Pro 플랜을 추천합니다", "confidence": 0.9},
        {"answer": "확실합니다", "confidence": 1.5},
        {"answer": "필드 누락"},
    ]
    for data in samples:
        try:
            reply = validate_output(data)
            print(f"  {data} → 통과: {reply.answer} ({reply.confidence})")
        except GuardError as exc:
            print(f"  {data} → {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
