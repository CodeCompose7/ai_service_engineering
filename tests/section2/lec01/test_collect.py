"""lec01 collect의 정제 로직 테스트.

네트워크 없이 도는 부분(clean·clean_text·보조 함수·로컬 CSV)만 검증한다.
from_web·from_api는 네트워크가 필요해 여기서 다루지 않는다.
"""

import pandas as pd

from section2.lec01.collect import (
    RAW_CSV,
    RAW_DOCS,
    clean,
    clean_text,
    clean_text_records,
    flag_outliers,
    from_csv,
    profile,
    to_dates,
)


def test_clean_strips_dedups_normalizes_coerces_drops():
    raw = pd.DataFrame(
        {
            "name": [" 텀블러", "노트북 ", "노트북 ", "키보드", None],
            "category": ["주방", "전자제품", "전자제품", "가전", "주방"],
            "price": ["12000", "1350000", "1350000", None, "9000"],
            "city": ["서울", " 부산", " 부산", "대구", "서울"],
        }
    )
    out = clean(raw)
    assert len(out) == 2
    assert out["name"].tolist() == ["텀블러", "노트북"]
    assert out["city"].tolist() == ["서울", "부산"]
    assert "전자제품" not in out["category"].tolist()
    assert set(out["category"]) <= {"주방", "전자"}
    assert out["price"].tolist() == [12000, 1350000]
    assert out["price"].dtype.kind in "fi"


def test_clean_keeps_rows_with_missing_nonessential():
    raw = pd.DataFrame(
        {"name": ["마우스"], "category": ["가전"], "price": ["25000"], "city": [None]}
    )
    out = clean(raw)
    assert len(out) == 1
    assert out["category"].iloc[0] == "전자"


def test_clean_does_not_mutate_input():
    raw = pd.DataFrame(
        {"name": [" a "], "category": ["주방"], "price": ["1"], "city": ["x"]}
    )
    clean(raw)
    assert raw["name"].iloc[0] == " a "


def test_from_csv_reads_bundled_raw():
    df = from_csv()
    assert list(df.columns) == ["id", "name", "category", "price", "city"]
    assert len(df) == 12


def test_clean_on_bundled_raw_drops_to_expected():
    out = clean(from_csv(RAW_CSV))
    assert len(out) == 8
    assert set(out["category"]) <= {"주방", "전자"}
    assert out["price"].dtype.kind in "fi"


def test_clean_text_collapses_whitespace_and_normalizes():
    assert clean_text("  배송이   빨라요.\n좋습니다.  ") == "배송이 빨라요. 좋습니다."
    assert clean_text("ＡＳＡＰ") == "ASAP"  # 전각 → 표준형
    assert clean_text(None) == ""


def test_clean_text_records_drops_short_empty_and_dups():
    out = clean_text_records(from_csv(RAW_DOCS))
    assert len(out) == 3  # 7건 → 빈·짧은 2건 제거, 중복 2건 합쳐 3건
    texts = out["text"].tolist()
    assert "배송이 빨라요. 좋습니다." in texts
    assert all(len(t) >= 4 for t in texts)
    assert len(set(texts)) == len(texts)


def test_to_dates_coerces_bad_to_nat():
    out = to_dates(pd.Series(["2026-01-03", "2026/01/04", "bad-date", ""]))
    assert int(out.notna().sum()) == 2
    assert int(out.isna().sum()) == 2


def test_flag_outliers_marks_far_values():
    s = pd.Series([10, 11, 12, 13, 12, 11, 1000])
    flags = flag_outliers(s)
    assert flags.iloc[-1]  # 1000은 이상치
    assert not flags.iloc[0]


def test_profile_counts_rows_dups_nulls():
    df = pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", "y"]})
    p = profile(df)
    assert p["rows"] == 3
    assert p["dups"] == 1
    assert p["nulls"] == {"a": 1}
