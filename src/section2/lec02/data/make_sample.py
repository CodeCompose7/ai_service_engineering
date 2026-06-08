"""sample.pdf 픽스처를 만드는 생성기. 한 번 실행해 같은 폴더에 sample.pdf를 만든다.

강의 본문이 아니라, 예제가 읽을 한국어 PDF를 재현 가능하게 만들어 두기 위한 도구다.
- 1쪽: 한국어 단락(텍스트). 텍스트박스가 줄을 접어 문장 중간에 줄바꿈이 들어간다.
- 2쪽: 1쪽을 이미지로 넣은 스캔본 흉내. 텍스트 레이어가 없어 추출하면 빈 문자열이 나온다.

실행:
    uv run python src/section2/lec02/data/make_sample.py
"""

from pathlib import Path

import fitz

PARA = (
    "아크메 주식회사 환불 규정\n"
    "고객은 상품 수령일로부터 7일 이내에 환불을 요청할 수 있습니다. "
    "단순 변심의 경우 왕복 배송비는 고객이 부담합니다. "
    "상품에 하자가 있으면 배송비를 포함해 전액 환불합니다."
)


def main() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 320, 420), PARA, fontname="korea", fontsize=12)
    pix = page.get_pixmap(dpi=72, colorspace=fitz.csGRAY)  # 새 페이지 추가 전에 렌더한다
    scan = doc.new_page()
    scan.insert_image(scan.rect, pixmap=pix)  # 텍스트 없는 이미지 전용 페이지
    out = Path(__file__).parent / "sample.pdf"
    doc.save(out)
    print(f"saved {out} ({doc.page_count} pages)")


if __name__ == "__main__":
    main()
