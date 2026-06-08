"""lec09 extract의 순수 로직 테스트.

네트워크 없이 도는 부분(출력 모델·백엔드 탐지·모델 문자열)만 검증한다.
instructor 호출 자체는 네트워크가 필요해 여기서 다루지 않는다.
"""

import pytest
from pydantic import ValidationError

from section1.lec09.extract import (
    CLOUD_MODEL,
    NormalizedReview,
    Review,
    ReviewReport,
    StrictKeywordReview,
    extract_review_safe,
    have_cloud,
    have_local,
    local_model,
    targets,
)


def test_review_accepts_valid_object():
    review = Review(sentiment="부정", confidence=0.8, keywords=["배송", "포장"])
    assert review.sentiment == "부정"
    assert 0.0 <= review.confidence <= 1.0


def test_review_rejects_out_of_set_sentiment():
    with pytest.raises(ValidationError):
        Review(sentiment="약간 부정", confidence=0.5, keywords=[])


def test_review_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Review(sentiment="긍정", confidence=1.5, keywords=[])


def test_normalized_review_absorbs_leading_space():
    review = NormalizedReview(sentiment=" 중립", confidence=0.9, keywords=["배송"])
    assert review.sentiment == "중립"


def test_strict_review_rejects_leading_space():
    with pytest.raises(ValidationError):
        Review(sentiment=" 중립", confidence=0.9, keywords=["배송"])


def test_have_cloud_and_local_read_env():
    assert have_cloud({"GEMINI_API_KEY": "x"}) is True
    assert have_cloud({}) is False
    assert have_local({"OLLAMA_API_BASE": "http://h:11434"}) is True
    assert have_local({}) is False


def test_local_model_uses_env_model():
    assert local_model({"OLLAMA_MODEL": "gemma4:12b"}) == "ollama/gemma4:12b"


def test_targets_detects_both_backends():
    env = {"GEMINI_API_KEY": "x", "OLLAMA_API_BASE": "http://h:11434", "OLLAMA_MODEL": "gemma4:12b"}
    result = targets(env)
    assert [label for label, _, _ in result] == ["클라우드", "로컬"]
    assert result[0][1] == CLOUD_MODEL
    assert result[1][2] == {"api_base": "http://h:11434"}


def test_targets_empty_when_nothing_ready():
    assert targets({}) == []


def test_targets_labels_cloud_model():
    env = {"OLLAMA_API_BASE": "http://h:11434", "OLLAMA_MODEL": "gemma4:31b-cloud"}
    label, model, _ = targets(env)[0]
    assert label == "Ollama Cloud"
    assert model == "ollama/gemma4:31b-cloud"


def test_targets_passes_api_key_when_set():
    env = {
        "OLLAMA_API_BASE": "http://h:11434",
        "OLLAMA_MODEL": "gemma4:31b-cloud",
        "OLLAMA_API_KEY": "k",
    }
    _, _, opts = targets(env)[0]
    assert opts["api_key"] == "k"


def test_targets_omits_api_key_when_absent():
    env = {"OLLAMA_API_BASE": "http://h:11434", "OLLAMA_MODEL": "gemma4:12b"}
    _, _, opts = targets(env)[0]
    assert "api_key" not in opts


def test_strict_keyword_review_rejects_multiword_keyword():
    # 한 단어 규칙을 어기면 검증에서 막힌다 (instructor 재시도를 부른다)
    with pytest.raises(ValidationError):
        StrictKeywordReview(sentiment="부정", confidence=0.8, keywords=["배송", "포장 허술"])


def test_strict_keyword_review_accepts_single_words():
    review = StrictKeywordReview(sentiment="부정", confidence=0.8, keywords=["배송", "포장"])
    assert review.keywords == ["배송", "포장"]


def test_review_report_nests_reviews():
    report = ReviewReport(
        overall="중립",
        aspects=[Review(sentiment="긍정", confidence=0.9, keywords=["배송"])],
        summary="대체로 무난",
    )
    assert report.aspects[0].sentiment == "긍정"
    assert report.overall == "중립"


def test_review_report_validates_nested_aspect():
    # 안쪽 Review의 제약(허용값)도 함께 검증된다
    with pytest.raises(ValidationError):
        ReviewReport(
            overall="중립",
            aspects=[Review(sentiment="아주 긍정", confidence=0.9, keywords=[])],
            summary="x",
        )


def test_extract_review_safe_raises_on_empty_models():
    with pytest.raises(ValueError):
        extract_review_safe("텍스트", models=[])


def test_backend_opts_picks_json_for_ollama():
    from section1.lec09.extract import NormalizedReview, _backend_opts

    assert _backend_opts("ollama/gemma4:31b-cloud") == (True, NormalizedReview)
    assert _backend_opts("gemini/gemini-2.5-flash") == (False, Review)


def test_make_client_mode_switches_with_json_mode():
    import instructor

    from section1.lec09.extract import make_client

    assert make_client(json_mode=False).mode == instructor.Mode.TOOLS
    assert make_client(json_mode=True).mode == instructor.Mode.JSON
