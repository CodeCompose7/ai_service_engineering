"""lec03 chunker의 청킹 로직 테스트.

입력은 lec02가 추출한 번들 문서(rag.pdf)라 네트워크 없이 결정적으로 돈다.
"""

from section2.lec03.chunker import (
    chunk_text,
    load_document_text,
    naive_chunks,
    overlap_between,
)


def test_naive_chunks_fixed_size():
    assert naive_chunks("abcdefg", 3) == ["abc", "def", "g"]


def test_naive_cuts_midword_recursive_keeps_words():
    sentence = "검색 증강 생성은 검색과 생성을 결합한 기술입니다."
    # 단순 분할은 8자에서 그냥 끊어 '생성|은'으로 단어를 가른다.
    assert naive_chunks(sentence, 8)[1].startswith("은")
    # 재귀 분할은 공백 경계를 지켜 '생성은'을 한 청크에 둔다.
    assert any("생성은" in c for c in chunk_text(sentence, 8, 0))


def test_chunks_respect_size():
    chunks = chunk_text(load_document_text(), 300, 0)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_overlap_increases_chunks_and_total():
    text = load_document_text()
    no_ov = chunk_text(text, 300, 0)
    ov = chunk_text(text, 300, 60)
    assert len(ov) > len(no_ov)  # 겹치니 청크가 더 많아진다
    assert sum(len(c) for c in ov) > sum(len(c) for c in no_ov)


def test_overlap_between_is_shared_tail_and_head():
    ov = chunk_text(load_document_text(), 300, 60)
    shared = overlap_between(ov[0], ov[1])
    assert len(shared) > 0
    assert ov[0].endswith(shared)
    assert ov[1].startswith(shared)


def test_overlap_between_empty_when_disjoint():
    assert overlap_between("abcdef", "xyz") == ""
