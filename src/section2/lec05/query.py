"""lec05 — 터미널에서 벡터DB를 조회하는 Read 래퍼(CLI).

영속 컬렉션을 열어 질문으로 검색한다. 컬렉션이 비어 있으면 rag.pdf를 한 번 인덱싱하고,
그 뒤로는 디스크에 남은 인덱스를 그대로 써서 질문만 임베딩해 검색한다.

실행:
    uv run python src/section2/lec05/query.py "검색 증강 생성이란?"
    uv run python src/section2/lec05/query.py "RAG의 한계는?" -k 5
    uv run python src/section2/lec05/query.py "정보를 어디서 가져오나" --source rag.pdf
"""

import argparse
from pathlib import Path

from section2.lec03.chunker import chunk_text, load_document_text
from section2.lec04.embedder import embed
from section2.lec05.store import build_index, make_collection, search

PERSIST_DIR = Path(__file__).parent / "data" / "chroma_db"  # .gitignore됨


def open_index():
    """영속 컬렉션을 연다. 비어 있으면 rag.pdf를 청킹·임베딩해 채운다."""
    collection = make_collection("rag_docs", persist_dir=PERSIST_DIR)
    if collection.count() == 0:
        chunks = chunk_text(load_document_text(), 500, 80)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metas = [{"source": "rag.pdf", "chunk": i} for i in range(len(chunks))]
        build_index(collection, chunks, metas, ids=ids)
        print(f"(인덱싱: rag.pdf {len(chunks)} 청크 → {PERSIST_DIR})")
    return collection


def main() -> int:
    parser = argparse.ArgumentParser(description="벡터DB에서 질문으로 청크를 검색한다")
    parser.add_argument("query", help="검색할 질문")
    parser.add_argument("-k", type=int, default=3, help="가져올 청크 수")
    parser.add_argument("--source", help="이 출처(메타데이터)로 검색을 제한")
    args = parser.parse_args()

    collection = open_index()
    where = {"source": args.source} if args.source else None
    hits = search(collection, embed(args.query), k=args.k, where=where)

    print(f"\n질문: {args.query}")
    for hit in hits:
        print(f"  {hit['similarity']:.3f} [{hit['metadata']['source']}] {hit['text'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
