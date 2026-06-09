"""lec05 store의 인덱싱·검색·필터 테스트.

가짜 임베딩으로 Chroma 동작만 검증한다. 실제 임베딩(bge-m3)은 무거워 예제 실행으로 본다.
"""

from section2.lec05.store import delete, get, index, make_collection, search, upsert


def _seed(col):
    index(
        col,
        ["환불 규정", "배송비 부담", "사내 공지"],
        [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]],
        metadatas=[{"src": "doc"}, {"src": "doc"}, {"src": "notice"}],
        ids=["x0", "x1", "x2"],
    )


def test_search_ranks_by_similarity():
    col = make_collection("rank_test")
    _seed(col)
    hits = search(col, [0.95, 0.1], k=2)
    assert hits[0]["text"] == "환불 규정"  # 질문 벡터에 가장 가까운 것
    assert hits[0]["similarity"] > hits[1]["similarity"]


def test_metadata_filter_restricts_search():
    col = make_collection("filter_test")
    _seed(col)
    hits = search(col, [0.95, 0.1], k=3, where={"src": "notice"})
    assert [h["metadata"]["src"] for h in hits] == ["notice"]  # 그 출처만 검색


def test_persistence_survives_reopen(tmp_path):
    col = make_collection("persist_test", persist_dir=tmp_path)
    index(col, ["청크 하나"], [[1.0, 0.0]], ids=["p0"])
    reopened = make_collection("persist_test", persist_dir=tmp_path)
    assert reopened.count() == 1  # 새 클라이언트로 열어도 유지


def test_get_reads_by_id_and_filter():
    col = make_collection("get_test")
    index(
        col,
        ["문서 청크", "공지 청크"],
        [[1.0, 0.0], [0.0, 1.0]],
        metadatas=[{"src": "doc"}, {"src": "notice"}],
        ids=["d0", "n0"],
    )
    by_id = get(col, ids=["d0"])
    assert by_id[0]["text"] == "문서 청크"
    by_filter = get(col, where={"src": "notice"})
    assert [h["id"] for h in by_filter] == ["n0"]  # 유사도 아닌 조건 조회


def test_upsert_updates_existing_and_delete_removes():
    col = make_collection("crud_test")
    index(col, ["원본 청크"], [[1.0, 0.0]], ids=["k0"])
    upsert(col, ["수정된 청크"], [[0.0, 1.0]], ids=["k0"])  # 같은 id를 갱신
    assert col.get(ids=["k0"])["documents"][0] == "수정된 청크"
    assert col.count() == 1  # 추가가 아니라 교체
    delete(col, ids=["k0"])
    assert col.count() == 0


def test_delete_by_metadata_filter():
    col = make_collection("crud_filter_test")
    index(
        col,
        ["문서 청크", "공지 청크"],
        [[1.0, 0.0], [0.0, 1.0]],
        metadatas=[{"src": "doc"}, {"src": "notice"}],
        ids=["d0", "n0"],
    )
    delete(col, where={"src": "notice"})  # 그 출처만 삭제
    assert col.count() == 1
    assert col.get()["metadatas"][0]["src"] == "doc"


def test_similarity_is_one_minus_cosine_distance():
    col = make_collection("sim_test")
    index(col, ["같은 방향"], [[1.0, 0.0]], ids=["s0"])
    hit = search(col, [1.0, 0.0], k=1)[0]
    assert hit["similarity"] > 0.99  # 같은 벡터면 유사도 ~1
