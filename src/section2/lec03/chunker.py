"""lec03 — 청킹.

lec02에서 뽑은 깨끗한 텍스트를 검색·임베딩에 알맞은 크기로 나눈다. 임베딩은 한 번에
담을 수 있는 길이가 정해져 있고, 너무 크면 검색 정밀도가 떨어지고 너무 작으면 맥락이
끊긴다. 그래서 적당한 크기로, 의미 단위를 지키며 자른다.

- 단순 고정 길이 분할은 단어·문장 중간을 끊는다.
- RecursiveCharacterTextSplitter는 문단 → 줄 → 문장 → 단어 순으로 큰 경계부터 시도해,
  가능한 한 의미 단위를 살린다.
- overlap으로 청크 경계에서 맥락이 끊기지 않게 앞뒤를 겹친다.

chunk_text가 산출물이다. 텍스트를 청크 목록으로 돌려준다.

실행:
    uv run python src/section2/lec03/chunker.py
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from section2.lec02.load import SAMPLE_PDF, extract_text

DEFAULT_SIZE = 500
DEFAULT_OVERLAP = 80
# 큰 경계부터 시도한다. 문단 → 줄 → 단어 → 글자. 큰 경계가 없으면 다음으로 내려간다.
SEPARATORS = ["\n\n", "\n", " ", ""]


def load_document_text() -> str:
    """lec02의 추출기로 rag.pdf 전체 텍스트를 한 덩어리로 가져온다. 청킹 입력이다."""
    return " ".join(page["text"] for page in extract_text(SAMPLE_PDF))


def naive_chunks(text: str, size: int = DEFAULT_SIZE) -> list[str]:
    """고정 길이로 자른다. 의미를 무시해 단어·문장 중간에서 끊긴다."""
    return [text[i : i + size] for i in range(0, len(text), size)]


def make_splitter(
    chunk_size: int = DEFAULT_SIZE, chunk_overlap: int = DEFAULT_OVERLAP
) -> RecursiveCharacterTextSplitter:
    """RecursiveCharacterTextSplitter를 우리 기본값으로 만든다."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=SEPARATORS
    )


def chunk_text(
    text: str, chunk_size: int = DEFAULT_SIZE, chunk_overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    """텍스트를 의미 단위를 지키며 청크로 나눈다. 이 단위의 산출물."""
    return make_splitter(chunk_size, chunk_overlap).split_text(text)


def _total(chunks: list[str]) -> int:
    return sum(len(c) for c in chunks)


def overlap_between(a: str, b: str) -> str:
    """앞 청크 a의 끝과 뒤 청크 b의 앞이 겹치는 부분을 찾는다. 없으면 빈 문자열."""
    for n in range(min(len(a), len(b)), 0, -1):
        if a[-n:] == b[:n]:
            return a[-n:]
    return ""


def main() -> int:
    text = load_document_text()
    print(f"입력: rag.pdf 정제 텍스트 {len(text)}자")

    print("\n=== 1. 단순 고정 분할 vs 재귀 분할 ===")
    sample = "검색 증강 생성은 검색과 생성을 결합한 기술입니다."
    print(f"문장: {sample}")
    print(f"  단순(8자): {naive_chunks(sample, 8)}")
    print(f"  재귀(8자): {chunk_text(sample, 8, 0)}")
    print("  단순은 단어 중간을 끊지만, 재귀는 공백 경계를 지킵니다")

    print("\n=== 2. overlap — 경계에서 맥락 잇기 ===")
    no_ov = chunk_text(text, 300, 0)
    ov = chunk_text(text, 300, 60)
    print(f"overlap 0 : {len(no_ov)}청크, 총 {_total(no_ov)}자")
    print(f"overlap 60: {len(ov)}청크, 총 {_total(ov)}자  (겹친 만큼 늘어남)")
    shared = overlap_between(ov[0], ov[1])
    print(f"  1·2번이 겹치는 부분({len(shared)}자): {shared!r}")

    print("\n=== 3. 청크 크기별 ===")
    for size in [200, 500, 1000]:
        chunks = chunk_text(text, size, 80)
        avg = _total(chunks) // len(chunks)
        print(f"  size={size:>4}: {len(chunks):>3}청크, 평균 {avg}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
