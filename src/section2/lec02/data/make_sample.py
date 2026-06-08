"""sample.pdf 픽스처를 만드는 생성기. 한 번 실행해 같은 폴더에 sample.pdf를 만든다.

강의 본문이 아니라, 예제가 읽을 한국어 PDF를 재현 가능하게 만들어 두기 위한 도구다.
보기 좋은 한국어를 위해 나눔고딕(OFL TrueType)을 내려받아 임베드하고, 저장 시 서브셋해
PDF를 작게 유지한다. 폰트 파일 자체는 저장소에 두지 않는다.

- 1쪽: 조문 형식의 한국어 사규(텍스트). 텍스트박스가 줄을 접어 문장 중간에 줄바꿈이 든다.
- 2쪽: 1쪽을 이미지로 넣은 스캔본 흉내. 텍스트 레이어가 없어 추출하면 빈 문자열이 나온다.

실행:
    uv run python src/section2/lec02/data/make_sample.py
"""

import tempfile
from pathlib import Path

import fitz
import httpx

FONT_URL = (
    "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
)

TITLE = "아크메 주식회사 환불 및 교환 규정"
BODY = (
    "제1조 (목적)\n"
    "이 규정은 아크메 주식회사가 판매하는 상품의 환불과 교환에 관한 기준을 정하는 것을 "
    "목적으로 합니다.\n\n"
    "제2조 (환불 요청 기간)\n"
    "고객은 상품을 받은 날로부터 7일 이내에 환불을 요청할 수 있습니다. 다만 식품 등 "
    "재판매가 어려운 상품은 환불이 제한될 수 있습니다.\n\n"
    "제3조 (배송비 부담)\n"
    "단순 변심으로 환불하는 경우 왕복 배송비는 고객이 부담합니다. 상품에 하자가 있거나 "
    "오배송된 경우에는 배송비를 포함해 전액을 환불합니다.\n\n"
    "제4조 (환불 처리 기간)\n"
    "환불은 반품된 상품을 확인한 뒤 3영업일 이내에 처리합니다. 결제 수단에 따라 실제 "
    "입금까지는 추가로 시간이 걸릴 수 있습니다."
)


def _download_font() -> str:
    path = Path(tempfile.gettempdir()) / "NanumGothic-Regular.ttf"
    if not path.exists():
        path.write_bytes(httpx.get(FONT_URL, follow_redirects=True, timeout=60).content)
    return str(path)


def main() -> None:
    font = _download_font()
    doc = fitz.open()
    page = doc.new_page()  # A4 기본
    page.insert_textbox(
        fitz.Rect(72, 72, 523, 110), TITLE, fontname="nanum", fontfile=font, fontsize=16
    )
    page.insert_textbox(
        fitz.Rect(72, 130, 523, 760), BODY, fontname="nanum", fontfile=font, fontsize=11
    )
    pix = page.get_pixmap(dpi=110, colorspace=fitz.csGRAY)  # 새 페이지 추가 전에 렌더
    scan = doc.new_page()
    scan.insert_image(scan.rect, pixmap=pix)  # 텍스트 없는 이미지 전용 페이지

    doc.subset_fonts()  # 쓰인 글자만 남겨 PDF를 작게
    out = Path(__file__).parent / "sample.pdf"
    doc.save(out, garbage=4, deflate=True)
    print(f"saved {out} ({doc.page_count} pages, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
