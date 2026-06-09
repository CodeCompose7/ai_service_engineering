"""lec05 — 벡터DB Chroma.

lec02~04가 여기서 한 파이프라인으로 모인다. rag.pdf를 로딩·청킹(lec02·lec03)하고,
청크를 임베딩(lec04)해 Chroma 컬렉션에 넣고, 질문으로 검색한다.

벡터DB는 두 가지를 해준다.
- 미리 계산한 임베딩을 저장한다. 질문마다 문서를 다시 임베딩하지 않는다.
- 수많은 벡터 중 가까운 것을 근사 최근접 이웃(ANN)으로 빠르게 찾는다.

거리 기준은 코사인으로 둔다. lec04의 코사인 유사도와 결을 맞추려고, 검색 결과의
similarity = 1 - 코사인 거리로 돌려준다. 메타데이터로 어느 문서·페이지인지 걸러낼 수 있다.

index·search가 산출물이다. (임베딩은 lec04 embed로, 원칙대로 LiteLLM 미경유 로컬 실행)

실행:
    uv run python src/section2/lec05/store.py
"""

import tempfile

import chromadb

from section2.lec03.chunker import chunk_text, load_document_text
from section2.lec04.embedder import embed

DEFAULT_NAME = "rag_docs"


def make_collection(name: str = DEFAULT_NAME, persist_dir=None):
    """Chroma 컬렉션을 만들거나 연다. persist_dir이 있으면 디스크에 영속된다."""
    if persist_dir:
        client = chromadb.PersistentClient(path=str(persist_dir))
    else:
        client = chromadb.EphemeralClient()
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def index(collection, documents, embeddings, metadatas=None, ids=None) -> None:
    """문서·임베딩·메타데이터를 컬렉션에 add한다. 임베딩은 호출부가 만들어 넘긴다."""
    ids = ids or [f"c{i}" for i in range(len(documents))]
    collection.add(
        ids=ids,
        documents=list(documents),
        embeddings=[[float(x) for x in e] for e in embeddings],
        metadatas=metadatas,
    )


def build_index(collection, documents, metadatas=None, ids=None) -> None:
    """문서를 lec04 embed로 임베딩해 컬렉션에 넣는다. 인덱싱 한 줄."""
    index(collection, documents, embed(documents), metadatas, ids)


def upsert(collection, documents, embeddings, metadatas=None, ids=None) -> None:
    """있으면 갱신, 없으면 추가한다. 문서가 바뀌면 그 청크를 다시 임베딩해 교체한다."""
    ids = ids or [f"c{i}" for i in range(len(documents))]
    collection.upsert(
        ids=ids,
        documents=list(documents),
        embeddings=[[float(x) for x in e] for e in embeddings],
        metadatas=metadatas,
    )


def delete(collection, ids=None, where=None) -> None:
    """id나 메타데이터 조건으로 청크를 지운다. 문서가 폐기되면 그 청크를 없앤다."""
    collection.delete(ids=ids, where=where)


def get(collection, ids=None, where=None, limit=None) -> list[dict]:
    """id나 메타데이터 조건으로 청크를 직접 꺼낸다. 유사도 검색이 아닌 조회(Read)다."""
    res = collection.get(ids=ids, where=where, limit=limit)
    return [
        {"id": i, "text": d, "metadata": m}
        for i, d, m in zip(res["ids"], res["documents"], res["metadatas"], strict=True)
    ]


def search(collection, query_embedding, k: int = 3, where=None) -> list[dict]:
    """질문 벡터에 가까운 청크 k개를 (텍스트·유사도·메타데이터)로 돌려준다. 유사도 기반 Read다."""
    res = collection.query(
        query_embeddings=[[float(x) for x in query_embedding]], n_results=k, where=where
    )
    hits = []
    for doc, dist, meta in zip(
        res["documents"][0], res["distances"][0], res["metadatas"][0], strict=True
    ):
        hits.append({"text": doc, "similarity": 1 - dist, "metadata": meta})
    return hits


def main() -> int:
    chunks = chunk_text(load_document_text(), 500, 80)
    notices = ["사내 식당은 정오에 엽니다.", "주차장은 지하 2층입니다."]
    print(f"입력: rag.pdf {len(chunks)} 청크 + 공지 {len(notices)}건")

    col = make_collection()
    chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]
    notice_ids = [f"notice_{i}" for i in range(len(notices))]
    metas = [{"source": "rag.pdf", "chunk": i} for i in range(len(chunks))]
    metas += [{"source": "notice", "chunk": i} for i in range(len(notices))]
    build_index(col, chunks + notices, metas, ids=chunk_ids + notice_ids)
    print(f"컬렉션에 {col.count()}개 저장")

    query = "검색 증강 생성은 어떻게 동작하나요?"
    qv = embed(query)
    print(f"\n=== 검색 — {query} ===")
    for hit in search(col, qv, k=3):
        print(f"  {hit['similarity']:.3f} [{hit['metadata']['source']}] {hit['text'][:36]}...")

    print("\n=== 메타데이터 필터 — source=notice 안에서만 ===")
    for hit in search(col, qv, k=2, where={"source": "notice"}):
        print(f"  {hit['similarity']:.3f} [{hit['metadata']['source']}] {hit['text']}")

    print("\n=== CRUD — 문서가 바뀌면 갱신·삭제 ===")
    changed = "주차장은 지하 3층으로 바뀌었습니다."
    upsert(
        col, [changed], embed([changed]),
        metadatas=[{"source": "notice", "chunk": 1}], ids=[notice_ids[1]],
    )
    print(f"  갱신(upsert): {col.get(ids=[notice_ids[1]])['documents'][0]}")
    delete(col, ids=[notice_ids[0]])
    print(f"  삭제(delete) 후 {col.count()}개")

    print("\n=== 영속성 — 디스크에 저장하면 재시작해도 유지 ===")
    with tempfile.TemporaryDirectory() as d:
        first = make_collection("persist_demo", persist_dir=d)
        index(first, ["테스트 청크"], embed(["테스트 청크"]), ids=["t0"])
        reopened = make_collection("persist_demo", persist_dir=d)
        print(f"  새 클라이언트로 다시 열어도 {reopened.count()}개 유지")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
