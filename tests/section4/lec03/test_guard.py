"""S4 lec03 가드레일 테스트.

허용 행동 제약·PII 마스킹·출력 검증을 본다.
"""

import pytest

from section4.lec02.harness import GuardError
from section4.lec03.guard import check_action, redact_pii, validate_output


def test_check_action_allows_listed():
    check_action("lookup")  # 예외 없음


def test_check_action_blocks_unlisted():
    with pytest.raises(GuardError):
        check_action("delete_account")


def test_redact_pii_masks_email_and_phone():
    out = redact_pii("alice@example.com / 010-1234-5678")
    assert "alice@example.com" not in out
    assert "010-1234-5678" not in out
    assert "[이메일]" in out
    assert "[전화]" in out


def test_validate_output_accepts_valid():
    assert validate_output({"answer": "네", "confidence": 0.8}).confidence == 0.8


def test_validate_output_rejects_out_of_range():
    with pytest.raises(GuardError):
        validate_output({"answer": "네", "confidence": 1.5})


def test_validate_output_rejects_missing_field():
    with pytest.raises(GuardError):
        validate_output({"answer": "네"})
