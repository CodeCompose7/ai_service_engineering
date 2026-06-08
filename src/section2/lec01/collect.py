"""lec01 — 데이터 수집·정제.

RAG에 넣기 전, 흩어진 원본 데이터를 한 DataFrame으로 모으고 가볍게 정제한다.
수집은 세 갈래다.

- CSV 파일: pd.read_csv(로컬 경로)
- 웹: pd.read_csv(URL)로 HTTP에 올라온 CSV·표를 바로 읽는다
- API: httpx로 JSON을 받아 DataFrame으로 만든다

정제는 데이터 모양에 따라 갈린다. 표 데이터는 공백·중복·표기·숫자·결측을 다루고
(clean), 텍스트는 공백·정규화·짧은·중복을 다룬다(clean_text_records). 이 둘이 산출물이다.
결측·날짜·이상치를 한 걸음 더 보는 보조 함수(to_dates·flag_outliers)와, 정제 전후를
숫자로 비교하는 profile도 함께 둔다. PDF·HTML 문서 추출은 lec02에서 다룬다.

실행:
    uv run python src/section2/lec01/collect.py
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
RAW_CSV = DATA_DIR / "raw_orders.csv"
RAW_DOCS = DATA_DIR / "raw_docs.csv"
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
    """표 데이터를 가볍게 정제한다. 원본은 건드리지 않고 새 DataFrame을 돌려준다."""
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


def clean_text(text: str) -> str:
    """한 덩어리 텍스트를 정제한다. 유니코드 정규화 후 연속 공백·개행을 한 칸으로 모은다."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)  # 전각·호환문자를 표준형으로
    text = re.sub(r"\s+", " ", text)  # 연속 공백·탭·개행을 한 칸으로
    return text.strip()


def clean_text_records(df: pd.DataFrame, col: str = "text", min_len: int = 4) -> pd.DataFrame:
    """텍스트 칼럼을 정제한다. 공백 정리 후 너무 짧거나 빈 행을 버리고 중복을 없앤다."""
    df = df.copy()
    df[col] = df[col].map(clean_text)
    df = df[df[col].str.len() >= min_len]
    return df.drop_duplicates(subset=[col]).reset_index(drop=True)


def to_dates(series: pd.Series) -> pd.Series:
    """여러 형식이 섞인 날짜 문자열을 datetime으로 바꾼다. 못 읽으면 NaT로 둔다."""
    return pd.to_datetime(series, errors="coerce", format="mixed")


def flag_outliers(series: pd.Series) -> pd.Series:
    """IQR 바깥 값을 이상치로 표시한다. 삭제가 아니라 검토 대상으로 골라낼 뿐이다."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)


def profile(df: pd.DataFrame) -> dict:
    """정제 전후를 비교할 작은 요약. 행 수·중복 수·결측 수를 센다."""
    nulls = df.isna().sum()
    return {
        "rows": int(len(df)),
        "dups": int(df.duplicated().sum()),
        "nulls": {col: int(n) for col, n in nulls.items() if n},
    }


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

    print("\n=== 2. 표 데이터 정제 + 프로파일 ===")
    cleaned = clean(raw)
    print(f"정제 전: {profile(raw)}")
    print(f"정제 후: {profile(cleaned)}")
    print("\n[정제 후]")
    print(cleaned.to_string(index=False))

    print("\n\n=== 3. 텍스트 정제 ===")
    docs = from_csv(RAW_DOCS)
    clean_docs = clean_text_records(docs)
    print(f"원본 {len(docs)}건 → 정제 {len(clean_docs)}건 (빈·짧은·중복 제거)")
    for text in clean_docs["text"]:
        print(f"  · {text}")

    print("\n=== 4. 심화 — 날짜 파싱 · 이상치 점검 ===")
    dates = to_dates(pd.Series(["2026-01-03", "2026/01/04", "bad-date", ""]))
    print(f"날짜: 4건 중 {int(dates.notna().sum())}건 파싱, {int(dates.isna().sum())}건 NaT")
    flagged = cleaned.loc[flag_outliers(cleaned["price"]), ["name", "price"]]
    print("가격 이상치(IQR 바깥):")
    print(flagged.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
