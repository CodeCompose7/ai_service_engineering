"""S4 lec06 — 실제 RAG 평가 (rag_eval.py).

toy 지식 주입 대신, S2에서 만든 진짜 RAG(Chroma 인덱스 + 문서)를 평가한다. 코퍼스는 RAG를
설명한 위키 문서다. RAG를 모델 단독과 견줘, 검색이 실제로 품질을 올리는지 본다.

핵심 질문: "우리 RAG가 그냥 모델에게 묻는 것보다 나은가." 그걸 점수로 답하고, 표로 낸다.
평가 부품(EvalHarness·judge)은 evaluate.py 것을 그대로 쓴다. answer_fn만 갈아 끼운다.

실행:
    uv run python src/section4/lec06/rag_eval.py
"""

import asyncio

from section2.lec06.mini_rag import answer, open_index
from section3.lec02.async_llm import acomplete
from section4.lec06.evaluate import EvalHarness

# 코퍼스(RAG 위키 문서)에 관한 질문. 일부는 일반, 일부는 문서에만 있는 세부다.
TESTSET = [
    {"q": "RAG란 무엇인가요?", "criteria": "LLM이 외부 정보를 검색해 통합하는 기법임을 설명한다"},
    {"q": "RAG라는 용어는 언제 어디서 처음 소개되었나요?",
     "criteria": "2020년 메타(Meta)의 연구 논문에서 소개되었음을 답한다"},
    {"q": "Retro 방식의 단점은 무엇인가요?",
     "criteria": "처음부터 훈련되어 높은 훈련 실행 비용이 든다는 점을 답한다"},
    {"q": "희소 벡터의 특징은 무엇인가요?",
     "criteria": "사전 길이이며 대부분 0을 포함한다는 점을 답한다"},
]

_COLLECTION = None


def _collection():
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = open_index()
    return _COLLECTION


async def rag_answer(question: str) -> str:
    """검색 + 생성. S2 RAG를 그대로 부른다."""
    return answer(_collection(), question, k=3)["answer"]


async def model_only(question: str) -> str:
    """검색 없이 모델 단독. 자기 지식만으로 답한다."""
    return await acomplete([
        {"role": "system", "content": "질문에 아는 대로 정확히 답한다."},
        {"role": "user", "content": question},
    ])


def _table(testset, rag: dict, alone: dict) -> None:
    print("| 질문 | RAG | 모델 단독 |")
    print("| --- | --- | --- |")
    for i, case in enumerate(testset):
        r = "PASS" if rag["results"][i]["passed"] else "FAIL"
        a = "PASS" if alone["results"][i]["passed"] else "FAIL"
        print(f"| {case['q']} | {r} | {a} |")
    print(f"| 점수 | {rag['score']:.0%} | {alone['score']:.0%} |")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    harness = EvalHarness(TESTSET)
    rag = asyncio.run(harness.run(rag_answer))
    alone = asyncio.run(harness.run(model_only))

    print("=== RAG vs 모델 단독 (S2 RAG 코퍼스: RAG 위키 문서) ===\n")
    _table(TESTSET, rag, alone)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
