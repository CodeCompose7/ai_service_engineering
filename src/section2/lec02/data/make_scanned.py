"""scanned.pdf 픽스처를 만든다. rag.pdf의 1쪽을 이미지로 구워 텍스트 레이어가 없는 1쪽 PDF로 만든다.

강의 본문이 아니라, 스캔본 PDF 함정(추출하면 빈 문자열)을 보여줄 샘플을 마련하는 도구다.

실행:
    uv run python src/section2/lec02/data/make_scanned.py
"""

from pathlib import Path

import fitz

DATA = Path(__file__).parent


def main() -> None:
    src = fitz.open(DATA / "rag.pdf")
    pix = src[0].get_pixmap(dpi=72, colorspace=fitz.csGRAY)
    out = fitz.open()
    page = out.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, pixmap=pix)  # 텍스트 없는 이미지 전용 페이지
    out.save(DATA / "scanned.pdf", garbage=4, deflate=True)
    kb = (DATA / "scanned.pdf").stat().st_size // 1024
    print(f"saved scanned.pdf ({kb} KB)")


if __name__ == "__main__":
    main()
