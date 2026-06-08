"""lec02 — 문서 로딩.

PDF·HTML에서 텍스트를 뽑는다. 추천 도구는 PyMuPDF(fitz) 하나다. PDF와 HTML을 같은
코드로 열고, 추출 품질도 좋다. 문서에서 텍스트를 꺼낼 때 자주 만나는 함정을 흡수한다.

- 줄바꿈: 줄을 접는 자리마다 문장 중간에 개행이 들어간다. 공백으로 잇는다.
- 정규화: 추출 텍스트가 자모로 분리(NFD)되기도 한다. NFC로 합친다.
- 스캔본: 이미지 전용 페이지는 텍스트 레이어가 없어 빈 문자열이 나온다. 표시해 OCR로 넘긴다.
- 보일러플레이트: 웹페이지는 내비게이션·푸터까지 함께 딸려 온다. 본문만 따로 추려야 한다.

extract_text가 산출물이다. 경로(.pdf·.html)를 주면 페이지별 정제 텍스트를 돌려준다.
샘플 문서는 한국어 위키백과 "검색 증강 생성" 글이다. CC BY-SA이며, 스캔본 흉내는
data/make_scanned.py로 만든다.

실행:
    uv run python src/section2/lec02/load.py
"""

import re
import unicodedata
from pathlib import Path

import fitz

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PDF = DATA_DIR / "rag.pdf"  # 실제 위키백과 PDF (여러 쪽, 텍스트)
SCANNED_PDF = DATA_DIR / "scanned.pdf"  # rag.pdf 1쪽을 이미지로 구운 스캔본 흉내
SAMPLE_HTML = DATA_DIR / "rag.html"  # 실제 위키백과 전체 페이지 HTML


def page_texts(path: Path | str) -> list[str]:
    """fitz로 문서를 열어 페이지별 원시 텍스트를 뽑는다. PDF·HTML 모두 같은 코드다."""
    with fitz.open(path) as doc:
        return [page.get_text() for page in doc]


def normalize(text: str) -> str:
    """문서 추출 함정을 흡수한다. NFC로 자모를 합치고, 줄바꿈·연속 공백을 한 칸으로 잇는다."""
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
    print(f"1쪽 원시: {raw[:48]!r} ...")
    print(f"  개행 {raw.count(chr(10))}개 — 줄을 접은 자리마다 끊깁니다")
    print(f"1쪽 정제: {normalize(raw)[:60]} ...")

    print("\n=== 2. 스캔본은 텍스트가 없습니다 ===")
    for label, path in [("rag.pdf    ", SAMPLE_PDF), ("scanned.pdf", SCANNED_PDF)]:
        pages = extract_text(path)
        empty = sum(p["is_empty"] for p in pages)
        mark = "  ← 스캔 이미지, OCR 필요" if empty else ""
        print(f"  {label}: {len(pages)}쪽, 빈 페이지 {empty}쪽{mark}")

    print("\n=== 3. HTML은 보일러플레이트까지 ===")
    print(f"  {extract_text(SAMPLE_HTML)[0]['text'][:75]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
