"""glossary 도구 테스트."""

from section3.lec01.tools.glossary import lookup_term


def test_lookup_term_found_and_loose():
    assert "검색 증강" in lookup_term("RAG")
    assert "벡터" in lookup_term("임베딩이 뭐야")  # 구절로 물어도 느슨히 매칭


def test_lookup_term_not_found():
    assert lookup_term("없는용어") == "사전에 없는 용어입니다."
