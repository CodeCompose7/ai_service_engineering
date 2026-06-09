"""lec07 — mini RAG 웹 조회·평가.

브라우저에서 질문을 검색·생성하고, EVAL_SET으로 검색 품질을 바로 평가한다. 임베딩 모델은
서버를 띄운 뒤 첫 요청에서 한 번만 메모리에 올라가고, 그 뒤 요청은 빠르다. lec05에서 말한
"한 번 로드, 여러 번 서빙"을 실제 서버로 보이는 셈이다.

생성은 lec06과 같이 LiteLLM을 거쳐 .env의 DEFAULT_PROVIDER로 한다.

실행:
    uv run uvicorn section2.lec07.app:app
    # 브라우저에서 http://127.0.0.1:8000 을 연다
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from section2.lec04.embedder import embed
from section2.lec05.crud import search
from section2.lec06.mini_rag import answer, open_index
from section2.lec07.evaluate import (
    EVAL_SET,
    K,
    first_relevant_rank,
    hit_rate_at_k,
    mean,
    reciprocal_rank,
)

app = FastAPI(title="mini RAG")

PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")

_collection = None


def collection():
    """영속 인덱스를 한 번만 연다. 첫 호출에서 모델과 인덱스가 준비된다."""
    global _collection
    if _collection is None:
        _collection = open_index()
    return _collection


@app.get("/api/query")
def api_query(q: str, k: int = 3):
    """질문을 검색·생성해 답과 근거를 돌려준다."""
    result = answer(collection(), q, k=k, window=1)
    sources = [
        {
            "rank": i + 1,
            "chunk": hit["metadata"]["chunk"],
            "similarity": round(hit["similarity"], 3),
            "text": hit["text"],
        }
        for i, hit in enumerate(result["hits"])
    ]
    return {"answer": result["answer"], "model": result["model"], "sources": sources}


@app.get("/api/eval")
def api_eval():
    """현재 인덱스에 EVAL_SET을 돌려 문항별 순위와 Hit Rate@k·MRR을 돌려준다."""
    col = collection()
    rows, hit_scores, rrs = [], [], []
    for item in EVAL_SET:
        hits = search(col, embed(item["q"]), k=K)
        rank = first_relevant_rank([h["text"] for h in hits], item["answer"])
        score = hit_rate_at_k(rank, K)
        hit_scores.append(score)
        rrs.append(reciprocal_rank(rank))
        rows.append({"q": item["q"], "answer": item["answer"], "rank": rank, "hit": bool(score)})
    return {
        "k": K,
        "hit_rate": round(mean(hit_scores), 2),
        "mrr": round(mean(rrs), 2),
        "rows": rows,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
