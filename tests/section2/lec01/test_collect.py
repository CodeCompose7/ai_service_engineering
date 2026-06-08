"""lec01 collect의 정제 로직 테스트.

네트워크 없이 도는 부분(clean·로컬 CSV)만 검증한다. from_web·from_api는 네트워크가
필요해 여기서 다루지 않는다.
"""

import pandas as pd

from section2.lec01.collect import RAW_CSV, clean, from_csv


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
    # 중복(노트북 행) 1개 + 필수 결측(키보드 price·마지막 name) 2개 제거 → 2행
    assert len(out) == 2
    assert out["name"].tolist() == ["텀블러", "노트북"]  # 앞뒤 공백 제거
    assert out["city"].tolist() == ["서울", "부산"]
    assert "전자제품" not in out["category"].tolist()  # 범주 표준화
    assert set(out["category"]) <= {"주방", "전자"}
    assert out["price"].tolist() == [12000, 1350000]  # 숫자 변환
    assert out["price"].dtype.kind in "fi"


def test_clean_keeps_rows_with_missing_nonessential():
    # city가 비어도 필수가 아니므로 행을 살린다. 가전은 전자로 표준화한다.
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
    before = raw["name"].iloc[0]
    clean(raw)
    assert raw["name"].iloc[0] == before  # 원본 보존


def test_from_csv_reads_bundled_raw():
    df = from_csv()
    assert list(df.columns) == ["id", "name", "category", "price", "city"]
    assert len(df) == 12


def test_clean_on_bundled_raw_drops_to_expected():
    out = clean(from_csv(RAW_CSV))
    assert len(out) == 8  # 12행에서 중복 1 + 결측 3 제거
    assert set(out["category"]) <= {"주방", "전자"}
    assert out["price"].dtype.kind in "fi"
