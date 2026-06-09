"""lec05 — 벡터DB CRUD 연산.

Chroma 컬렉션을 만들고, 청크·임베딩·메타데이터를 넣고·읽고·고치고·지운다. 이 연산들이
이 단위의 산출물이다. 임베딩은 lec04 embed로 만들어 넘긴다. 원칙대로 LiteLLM을 거치지
않고 bge-m3를 로컬에서 직접 돌리는 임베딩을 그대로 쓴다.

거리 기준은 코사인으로 둔다. lec04의 코사인 유사도와 결을 맞추려고, search는
similarity = 1 - 코사인 거리로 돌려준다.
"""

import chromadb

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
    """Create — 문서·임베딩·메타데이터를 컬렉션에 add한다. 임베딩은 호출부가 만들어 넘긴다."""
    ids = ids or [f"c{i}" for i in range(len(documents))]
    collection.add(
        ids=ids,
        documents=list(documents),
        embeddings=[[float(x) for x in e] for e in embeddings],
        metadatas=metadatas,
    )


def build_index(collection, documents, metadatas=None, ids=None) -> None:
    """Create — 문서를 lec04 embed로 임베딩해 컬렉션에 넣는다. 인덱싱 한 줄."""
    index(collection, documents, embed(documents), metadatas, ids)


def get(collection, ids=None, where=None, limit=None) -> list[dict]:
    """Read — id나 메타데이터 조건으로 청크를 직접 꺼낸다. 유사도 검색이 아닌 조회다."""
    res = collection.get(ids=ids, where=where, limit=limit)
    return [
        {"id": i, "text": d, "metadata": m}
        for i, d, m in zip(res["ids"], res["documents"], res["metadatas"], strict=True)
    ]


def search(collection, query_embedding, k: int = 3, where=None) -> list[dict]:
    """Read — 질문 벡터에 가까운 청크 k개를 (텍스트·유사도·메타데이터)로 돌려준다."""
    res = collection.query(
        query_embeddings=[[float(x) for x in query_embedding]], n_results=k, where=where
    )
    hits = []
    for doc, dist, meta in zip(
        res["documents"][0], res["distances"][0], res["metadatas"][0], strict=True
    ):
        hits.append({"text": doc, "similarity": 1 - dist, "metadata": meta})
    return hits


def upsert(collection, documents, embeddings, metadatas=None, ids=None) -> None:
    """Update — 있으면 갱신, 없으면 추가한다. 문서가 바뀌면 그 청크를 다시 임베딩해 교체한다."""
    ids = ids or [f"c{i}" for i in range(len(documents))]
    collection.upsert(
        ids=ids,
        documents=list(documents),
        embeddings=[[float(x) for x in e] for e in embeddings],
        metadatas=metadatas,
    )


def delete(collection, ids=None, where=None) -> None:
    """Delete — id나 메타데이터 조건으로 청크를 지운다. 문서가 폐기되면 그 청크를 없앤다."""
    collection.delete(ids=ids, where=where)
