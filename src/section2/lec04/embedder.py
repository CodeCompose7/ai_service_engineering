"""lec04 — 임베딩.

텍스트를 의미를 담은 벡터로 바꾼다. 생성 LLM과 달리 임베딩은 LiteLLM을 경유하지 않고
sentence-transformers로 HF 모델(bge-m3)을 로컬 CPU에서 직접 돌린다. 키가 필요 없고,
모델은 최초 실행 시 자동으로 받는다. (S2 개요에서 예고한 LiteLLM 미경유 예외)

비슷한 뜻의 문장은 벡터가 가깝고(코사인 유사도가 높음), 무관하면 멀다. 이 유사도가 RAG
검색의 바탕이다. lec03의 청크를 여기서 벡터로 바꾸고, lec05에서 벡터DB에 넣는다.

embed가 산출물이다. 텍스트(또는 목록)를 정규화된 벡터로 돌려준다.

실행:
    uv run python src/section2/lec04/embedder.py
"""

import os

import numpy as np

DEFAULT_MODEL = "BAAI/bge-m3"

_model = None


def get_model(name: str | None = None):
    """sentence-transformers 모델을 한 번만 로드해 재사용한다. 최초 실행 시 자동 다운로드한다."""
    global _model
    name = name or os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL)
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(name)
    return _model


def embed(texts: str | list[str]) -> np.ndarray:
    """텍스트(또는 목록)를 정규화된 벡터로 임베딩한다. 이 단위의 산출물.

    벡터를 정규화하므로 코사인 유사도는 내적으로 계산된다. 문자열 하나면 1차원 벡터를,
    목록이면 (개수, 차원) 배열을 돌려준다.
    """
    single = isinstance(texts, str)
    batch = [texts] if single else list(texts)
    vecs = get_model().encode(batch, normalize_embeddings=True)
    return vecs[0] if single else vecs


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """두 벡터의 코사인 유사도. 정규화된 벡터에서는 내적과 같다."""
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def rank(query_vec: np.ndarray, candidates: list[str], candidate_vecs) -> list[tuple[str, float]]:
    """query 벡터에 가까운 순서로 (후보, 유사도)를 정렬한다. 모델 없이 도는 순수 로직이다."""
    scored = [(c, cosine(query_vec, cv)) for c, cv in zip(candidates, candidate_vecs, strict=True)]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def most_similar(query: str, candidates: list[str]) -> list[tuple[str, float]]:
    """query를 후보들과 임베딩해, 가까운 순으로 정렬한다. 검색의 가장 단순한 형태다."""
    return rank(embed(query), candidates, embed(candidates))


def main() -> int:
    print("=== 1. 텍스트 → 벡터 ===")
    vec = embed("검색 증강 생성은 검색과 생성을 결합합니다.")
    print(f"문장 하나 → {vec.shape[0]}차원 벡터")
    print(f"  앞 5개 값: {[round(float(x), 3) for x in vec[:5]]}")

    print("\n=== 2. 유사도 직관 — 비슷하면 가깝다 ===")
    pairs = [
        ("환불은 7일 이내 가능합니다.", "반품 기한은 일주일입니다.", "비슷"),
        ("환불은 7일 이내 가능합니다.", "오늘 서울 날씨는 맑습니다.", "무관"),
    ]
    for a, b, tag in pairs:
        s = cosine(embed(a), embed(b))
        print(f"  [{tag}] {s:.3f}  · {a} ↔ {b}")

    print("\n=== 3. 검색 맛보기 — 질문에 가까운 청크 고르기 ===")
    query = "환불 기간이 어떻게 되나요?"
    candidates = [
        "고객은 상품 수령일로부터 7일 이내에 환불을 요청할 수 있습니다.",
        "단순 변심의 경우 왕복 배송비는 고객이 부담합니다.",
        "회사는 매주 월요일에 전체 회의를 엽니다.",
        "신제품은 다음 분기에 출시될 예정입니다.",
    ]
    print(f"질문: {query}")
    for text, score in most_similar(query, candidates):
        print(f"  {score:.3f}  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
