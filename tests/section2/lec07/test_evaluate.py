"""lec07 evaluate의 지표 로직 테스트.

순위·Recall@k·MRR 계산을 모델 없이 검증한다. 실제 검색·임베딩이 도는 설정 비교는
무거워 예제 실행으로 확인한다.
"""

from section2.lec07.evaluate import (
    first_relevant_rank,
    mean,
    recall_at_k,
    reciprocal_rank,
)


def test_first_relevant_rank_finds_position():
    texts = ["관련 없음", "정답 문구가 여기 있다", "또 다른 청크"]
    assert first_relevant_rank(texts, "정답 문구") == 2


def test_first_relevant_rank_ignores_spaces():
    # PDF 공백 노이즈가 껴 있어도 공백을 지우고 맞춘다
    assert first_relevant_rank(["새로운 정보를 검 색하고"], "새로운 정보를 검색") == 1


def test_first_relevant_rank_zero_when_absent():
    assert first_relevant_rank(["a", "b"], "없는 문구") == 0


def test_recall_at_k_threshold():
    assert recall_at_k(3, 5) == 1.0  # 5위 안
    assert recall_at_k(6, 5) == 0.0  # 5위 밖
    assert recall_at_k(0, 5) == 0.0  # 못 찾음


def test_reciprocal_rank():
    assert reciprocal_rank(1) == 1.0
    assert reciprocal_rank(4) == 0.25
    assert reciprocal_rank(0) == 0.0


def test_mean():
    assert mean([1.0, 0.0, 0.0]) == 1 / 3
    assert mean([]) == 0.0
