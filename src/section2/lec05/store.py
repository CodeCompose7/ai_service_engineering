"""lec05 — rag.pdf를 벡터DB에 인덱싱하고 검색·CRUD·영속을 시연한다.

crud.py의 연산으로 lec02~04를 한 파이프라인으로 잇는다. rag.pdf를 로딩·청킹(lec02·lec03)하고
청크를 임베딩(lec04)해 Chroma에 넣고, 질문으로 검색하며, 메타데이터 필터·갱신·삭제·영속을
차례로 보여준다.

실행:
    uv run python src/section2/lec05/store.py
"""

import tempfile

from section2.lec03.chunker import chunk_text, load_document_text
from section2.lec04.embedder import embed
from section2.lec05.crud import (
    build_index,
    delete,
    get,
    index,
    make_collection,
    search,
    upsert,
)


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
    print(f"  갱신(upsert): {get(col, ids=[notice_ids[1]])[0]['text']}")
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
