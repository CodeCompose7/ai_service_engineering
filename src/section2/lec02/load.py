"""lec02 — 문서 로딩.

PDF·HTML에서 텍스트를 뽑는다. 추천 도구는 PyMuPDF(fitz) 하나다. PDF와 HTML을 같은
코드로 열고, 추출 품질도 좋다. 한국어 PDF에서 자주 만나는 함정을 흡수한다.

- 줄바꿈: 텍스트박스가 줄을 접어 문장 중간에 개행이 들어간다. 공백으로 잇는다.
- 정규화: 추출 텍스트가 자모로 분리(NFD)되기도 한다. NFC로 합친다.
- 스캔본: 이미지 전용 페이지는 텍스트 레이어가 없어 빈 문자열이 나온다. 표시해 OCR로 넘긴다.

extract_text가 산출물이다. 경로(.pdf·.html)를 주면 페이지별 정제 텍스트를 돌려준다.

실행:
    uv run python src/section2/lec02/load.py
"""

import re
import unicodedata
from pathlib import Path

import fitz

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PDF = DATA_DIR / "sample.pdf"
SAMPLE_HTML = DATA_DIR / "sample.html"


def page_texts(path: Path | str) -> list[str]:
    """fitz로 문서를 열어 페이지별 원시 텍스트를 뽑는다. PDF·HTML 모두 같은 코드다."""
    with fitz.open(path) as doc:
        return [page.get_text() for page in doc]


def normalize(text: str) -> str:
    """한국어 PDF 함정을 흡수한다. NFC로 자모를 합치고, 줄바꿈·연속 공백을 한 칸으로 잇는다."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_text(path: Path | str, *, clean: bool = True) -> list[dict]:
    """문서에서 페이지별 텍스트를 뽑는다. 산출물.

    각 항목은 {page, text, chars, is_empty}이다. 텍스트가 없는 페이지(스캔 이미지 등)는
    is_empty=True로 표시해, OCR이 필요함을 알린다.
    """
    pages = []
    for i, raw in enumerate(page_texts(path), start=1):
        text = normalize(raw) if clean else raw
        pages.append(
            {"page": i, "text": text, "chars": len(text), "is_empty": len(text) == 0}
        )
    return pages


def main() -> int:
    print("=== 1. PDF 원시 추출 vs 정제 ===")
    raw = page_texts(SAMPLE_PDF)[0]
    print(f"1쪽 원시: {raw[:55]!r} ...")
    print(f"  개행 {raw.count(chr(10))}개 — 문장이 줄 단위로 끊깁니다")
    print(f"1쪽 정제: {normalize(raw)[:70]} ...")

    print("\n=== 2. 페이지별 추출 결과 ===")
    for page in extract_text(SAMPLE_PDF):
        mark = "  ← 빈 페이지(스캔 이미지?), OCR 필요" if page["is_empty"] else ""
        print(f"  {page['page']}쪽: {page['chars']}자{mark}")

    print("\n=== 3. HTML도 같은 코드로 ===")
    for page in extract_text(SAMPLE_HTML):
        print(f"  {page['text'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
