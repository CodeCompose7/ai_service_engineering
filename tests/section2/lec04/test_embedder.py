"""lec04 embedder의 순수 로직 테스트.

코사인 유사도와 정렬은 모델 없이 검증한다. 실제 임베딩(bge-m3 로드)은 무겁고 느려
단위 테스트에서 다루지 않고, 예제 실행으로 확인한다.
"""

import numpy as np

from section2.lec04.embedder import cosine, rank


def test_cosine_identical_orthogonal_opposite():
    a = np.array([1.0, 0.0])
    assert cosine(a, a) == 1.0
    assert cosine(a, np.array([0.0, 1.0])) == 0.0
    assert cosine(a, np.array([-1.0, 0.0])) == -1.0


def test_cosine_ignores_magnitude():
    # 코사인은 방향만 본다. 같은 방향이면 크기가 달라도 1
    assert abs(cosine(np.array([1.0, 1.0]), np.array([3.0, 3.0])) - 1.0) < 1e-9


def test_rank_orders_by_similarity():
    query = np.array([1.0, 0.0])
    candidates = ["가깝다", "직각", "반대"]
    vecs = [np.array([0.9, 0.1]), np.array([0.0, 1.0]), np.array([-1.0, 0.0])]
    ranked = rank(query, candidates, vecs)
    assert [c for c, _ in ranked] == ["가깝다", "직각", "반대"]
    assert ranked[0][1] > ranked[1][1] > ranked[2][1]
