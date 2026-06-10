"""lec07 — 검색 평가.

mini RAG의 품질은 거의 검색이 정답 근거를 찾느냐에 달려 있다. 그래서 감이 아니라 숫자로
잰다. 질문과 정답 근거(그 청크에 있어야 할 문구)를 미리 정해 두고, 청킹 설정을 바꿔가며
top-k 검색이 정답을 얼마나 잘 가져오는지 두 지표로 비교한다.

- Hit Rate@k: 상위 k개 안에 정답 근거가 들어 있으면 1, 아니면 0. 평균이 적중률이다.
- MRR: 정답 근거가 처음 나온 순위의 역수(1/순위). 위쪽에 나올수록 높다.

정답은 청크 텍스트에 정답 문구가 들어 있는지로 판정한다. 청크 경계는 설정마다 달라지지만
문구는 그대로라, 설정을 바꿔도 같은 잣대로 비교된다. PDF 추출의 공백 노이즈를 피하려고
공백을 지우고 비교한다.

실행:
    uv run python src/section2/lec07/evaluate.py
"""

from section2.lec03.chunker import chunk_text, load_document_text
from section2.lec04.embedder import embed
from section2.lec05.crud import build_index, make_collection, search

K = 5

# 질문과 정답 근거 문구. 그 문구가 든 청크가 정답이다.
EVAL_SET = [
    {"q": "검색 증강 생성은 무엇인가요?", "answer": "새로운 정보를 검색"},
    {"q": "참조 데이터는 어디에 저장되나요?", "answer": "벡터 데이터베이스"},
    {"q": "검색된 정보는 어떻게 LLM에 전달되나요?", "answer": "프롬프트 엔지니어링"},
    {"q": "RAG와 관련된 보안 문제는 무엇인가요?", "answer": "보안"},
    {"q": "RAG는 환각과 어떤 관련이 있나요?", "answer": "환각"},
]

CONFIGS = [
    {"chunk_size": 300, "overlap": 50},
    {"chunk_size": 500, "overlap": 80},
    {"chunk_size": 1000, "overlap": 150},
]


def first_relevant_rank(texts: list[str], answer: str) -> int:
    """검색 결과 텍스트들 중 정답 문구가 처음 나온 순위(1부터)를 돌려준다. 없으면 0.

    PDF 추출의 군더더기 공백을 피하려고 양쪽 모두 공백을 지우고 비교한다.
    """
    target = answer.replace(" ", "")
    for rank, text in enumerate(texts, 1):
        if target in text.replace(" ", ""):
            return rank
    return 0


def hit_rate_at_k(rank: int, k: int) -> float:
    """정답이 상위 k 안에 있으면 1.0, 아니면 0.0. 정답이 질문당 하나면 Recall@k와 같다."""
    return 1.0 if 0 < rank <= k else 0.0


def reciprocal_rank(rank: int) -> float:
    """정답 순위의 역수. 못 찾았으면 0.0."""
    return 1.0 / rank if rank > 0 else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_config(eval_set, chunk_size: int, overlap: int, k: int = K) -> dict:
    """한 청킹 설정으로 인덱스를 만들고 평가셋을 검색해 Hit Rate@k와 MRR을 잰다."""
    chunks = chunk_text(load_document_text(), chunk_size, overlap)
    collection = make_collection(f"eval_{chunk_size}_{overlap}")
    build_index(collection, chunks, ids=[f"c{i}" for i in range(len(chunks))])

    hit_scores, rrs = [], []
    for item in eval_set:
        hits = search(collection, embed(item["q"]), k=k)
        rank = first_relevant_rank([h["text"] for h in hits], item["answer"])
        hit_scores.append(hit_rate_at_k(rank, k))
        rrs.append(reciprocal_rank(rank))
    return {"chunks": len(chunks), "hit_rate": mean(hit_scores), "mrr": mean(rrs)}


def main() -> int:
    print(f"평가셋 {len(EVAL_SET)}문항, top-{K} 검색\n")
    print(f"{'size':>5} {'overlap':>7} {'chunks':>6} {'Hit@' + str(K):>9} {'MRR':>5}")
    for cfg in CONFIGS:
        m = evaluate_config(EVAL_SET, cfg["chunk_size"], cfg["overlap"])
        print(
            f"{cfg['chunk_size']:>5} {cfg['overlap']:>7} {m['chunks']:>6} "
            f"{m['hit_rate']:>9.2f} {m['mrr']:>5.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
