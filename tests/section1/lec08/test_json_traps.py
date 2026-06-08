"""lec08 json_traps의 순수 로직 테스트.

네트워크 없이 도는 부분(Pydantic 계약·JSON 가드·검증)만 검증한다.
"""

import pytest
from pydantic import ValidationError

from section1.lec08.json_traps import (
    Review,
    extract_json,
    parse_with_guard,
    raw_parses,
    targets,
    validate,
)

GOOD = {"sentiment": "부정", "confidence": 0.8, "keywords": ["배송", "포장"]}


def test_review_accepts_valid_contract():
    review = Review(**GOOD)
    assert review.sentiment == "부정"
    assert review.confidence == 0.8


def test_review_rejects_out_of_set_sentiment():
    with pytest.raises(ValidationError):
        Review(sentiment="약간 부정", confidence=0.5, keywords=[])


def test_review_rejects_non_float_confidence():
    with pytest.raises(ValidationError):
        Review(sentiment="긍정", confidence="높음", keywords=[])


def test_review_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Review(sentiment="긍정", confidence=1.5, keywords=[])


def test_extract_json_strips_code_fence():
    text = '```json\n{"a": 1}\n```'
    assert extract_json(text) == '{"a": 1}'


def test_extract_json_drops_surrounding_text():
    text = '이 리뷰는 부정입니다. {"sentiment": "부정"} 도움이 됐길 바랍니다.'
    assert extract_json(text) == '{"sentiment": "부정"}'


def test_raw_parses_false_on_fenced_json():
    assert raw_parses('```json\n{"a": 1}\n```') is False
    assert raw_parses('{"a": 1}') is True


def test_parse_with_guard_recovers_fenced_json():
    assert parse_with_guard('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_with_guard_returns_none_on_garbage():
    assert parse_with_guard("그냥 문장입니다") is None


def test_validate_passes_good_contract():
    ok, err = validate(GOOD)
    assert ok is True
    assert err == ""


def test_validate_reports_first_error():
    ok, err = validate({"sentiment": "약간 부정", "confidence": 0.5, "keywords": []})
    assert ok is False
    assert "sentiment" in err


def test_targets_detects_backends():
    env = {"GEMINI_API_KEY": "x", "OLLAMA_API_BASE": "http://h:11434", "OLLAMA_MODEL": "gemma4:12b"}
    labels = [label for label, _, _ in targets(env)]
    assert labels == ["클라우드", "로컬"]
