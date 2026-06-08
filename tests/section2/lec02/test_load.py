"""lec02 load의 추출·정제 테스트.

번들 문서(실제 위키백과 "검색 증강 생성" PDF·HTML과 스캔본 흉내)는 저장소에 들어 있어
네트워크 없이 결정적으로 돈다.
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
    assert nfd != "환불"
    assert normalize(nfd + "\n규정") == "환불 규정"


def test_extract_text_pdf_has_text_on_every_page():
    pages = extract_text(SAMPLE_PDF)
    assert len(pages) >= 5
    assert all(not p["is_empty"] for p in pages)  # 텍스트 PDF는 빈 페이지가 없다
    assert "증강" in pages[0]["text"]


def test_extract_text_pdf_clean_has_no_internal_newline():
    assert "\n" not in extract_text(SAMPLE_PDF)[0]["text"]  # 줄바꿈이 공백으로 이어졌다


def test_raw_pdf_page_has_internal_newlines():
    assert page_texts(SAMPLE_PDF)[0].count("\n") >= 5  # 원시 추출엔 줄바꿈이 많다


def test_extract_text_html_includes_body_and_boilerplate():
    full = " ".join(p["text"] for p in extract_text(SAMPLE_HTML))
    assert "검색" in full  # 본문이 들어온다
    assert "주 메뉴" in full  # 내비게이션 보일러플레이트까지 함께 들어온다
