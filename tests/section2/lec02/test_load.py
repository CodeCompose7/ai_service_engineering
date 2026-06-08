"""lec02 load의 추출·정제 테스트.

번들 PDF·HTML은 저장소에 들어 있어 네트워크 없이 결정적으로 돈다.
"""

import unicodedata

from section2.lec02.load import (
    SAMPLE_HTML,
    SAMPLE_PDF,
    extract_text,
    normalize,
    page_texts,
)


def test_normalize_joins_linebreaks_and_collapses_spaces():
    assert normalize("가\n나   다\n") == "가 나 다"


def test_normalize_recomposes_nfd_jamo():
    nfd = unicodedata.normalize("NFD", "환불")  # 자모로 분리된 형태
    assert nfd != "환불"  # 분리되어 원문과 다르다
    assert normalize(nfd + "\n규정") == "환불 규정"  # NFC로 합쳐진다


def test_extract_text_pdf_flags_empty_scanned_page():
    pages = extract_text(SAMPLE_PDF)
    assert len(pages) == 2
    assert pages[0]["chars"] > 0
    assert pages[0]["is_empty"] is False
    assert "아크메" in pages[0]["text"]
    assert pages[1]["is_empty"] is True  # 이미지 전용 페이지


def test_extract_text_pdf_clean_has_no_internal_newline():
    text = extract_text(SAMPLE_PDF)[0]["text"]
    assert "\n" not in text  # 줄바꿈이 공백으로 이어졌다


def test_raw_page_has_internal_newlines():
    raw = page_texts(SAMPLE_PDF)[0]
    assert raw.count("\n") >= 2  # 원시 추출에는 문장 중간 개행이 있다


def test_extract_text_html_same_code():
    pages = extract_text(SAMPLE_HTML)
    assert len(pages) >= 1
    assert "아크메" in pages[0]["text"]
    assert "console.log" not in pages[0]["text"]  # script 텍스트는 본문이 아니다
