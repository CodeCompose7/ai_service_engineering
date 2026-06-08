"""lec01 — 데이터 수집·정제.

RAG에 넣기 전, 흩어진 원본 데이터를 한 DataFrame으로 모으고 가볍게 정제한다.
수집은 세 갈래다.

- CSV 파일: pd.read_csv(로컬 경로)
- 웹: pd.read_csv(URL)로 HTTP에 올라온 CSV·표를 바로 읽는다
- API: httpx로 JSON을 받아 DataFrame으로 만든다

clean이 이 단위의 산출물이다. 공백 제거·중복 제거·범주 표준화·숫자 변환·필수 결측
제거를 pandas로 한 번에 처리한다. (PDF·HTML 문서에서 텍스트를 뽑는 일은 lec02에서 다룬다)

실행:
    uv run python src/section2/lec01/collect.py
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
RAW_CSV = DATA_DIR / "raw_orders.csv"
WEB_CSV_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
API_URL = "https://jsonplaceholder.typicode.com/posts"

# 같은 범주를 가리키는 다른 표기를 하나로 모은다.
CATEGORY_MAP = {"주방용품": "주방", "전자제품": "전자", "가전": "전자"}


def from_csv(path: Path | str = RAW_CSV) -> pd.DataFrame:
    """로컬 CSV 파일을 읽는다."""
    return pd.read_csv(path)


def from_web(url: str = WEB_CSV_URL) -> pd.DataFrame:
    """웹에 올라온 CSV를 URL로 바로 읽는다."""
    return pd.read_csv(url)


def from_api(url: str = API_URL) -> pd.DataFrame:
    """JSON API를 호출해 레코드 목록을 DataFrame으로 만든다."""
    import httpx

    rows = httpx.get(url, timeout=15).json()
    return pd.DataFrame(rows)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """수집한 주문 데이터를 가볍게 정제한다. 원본은 건드리지 않고 새 DataFrame을 돌려준다."""
    df = df.copy()
    df.columns = df.columns.str.strip()  # 헤더 공백 제거

    # 1) 문자열 칼럼의 앞뒤 공백을 떼어낸다.
    for col in ["name", "category", "city"]:
        df[col] = df[col].str.strip()

    # 2) 완전히 같은 행을 한 번만 남긴다.
    df = df.drop_duplicates()

    # 3) 같은 뜻의 범주 표기를 표준값으로 모은다.
    df["category"] = df["category"].replace(CATEGORY_MAP)

    # 4) 가격을 숫자로 바꾼다. 숫자가 아니면 결측으로 둔다.
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # 5) 필수 값(name·price)이 빈 행은 버린다. city 같은 그 밖의 결측은 그대로 둔다.
    keep = df["name"].notna() & (df["name"] != "") & df["price"].notna()
    df = df[keep].reset_index(drop=True)

    # 6) 결측을 버렸으니 가격을 정수로 떨군다.
    df["price"] = df["price"].astype(int)
    return df


def _shape(df: pd.DataFrame) -> str:
    return f"{df.shape[0]}행 {df.shape[1]}열"


def main() -> int:
    print("=== 1. 수집 — CSV · 웹 · API ===")
    raw = from_csv()
    print(f"CSV : {RAW_CSV.name} → {_shape(raw)}")
    for label, fn in [("웹 ", from_web), ("API", from_api)]:
        try:
            df = fn()
            print(f"{label} : {_shape(df)}  {list(df.columns)[:4]}")
        except Exception as exc:
            print(f"{label} : 건너뜀 ({type(exc).__name__}) — 네트워크를 확인하세요")

    print("\n=== 2. pandas 경량 정제 ===")
    cleaned = clean(raw)
    removed = len(raw) - len(cleaned)
    print(f"원본 {len(raw)}행 → 정제 {len(cleaned)}행 (중복·결측 {removed}행 제거)")
    print("\n[정제 후]")
    print(cleaned.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
