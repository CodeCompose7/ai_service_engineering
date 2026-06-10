"""S4 lec06 — 다중 에이전트 벤치마크 (benchmark.py).

평가가 의미 있으려면 한 에이전트의 유무가 아니라, 후보 여럿을 같은 잣대로 견줘야 한다. 그리고
품질만이 아니라 비용도 함께 봐야 한다. 품질은 PASS/FAIL이 아니라 0~5 점수로 잰다.

여기서는 세 에이전트를 같은 테스트셋으로 돌려 표 하나에 놓는다.

- 모델 단독: 검색 없이 모델 지식만.
- RAG k=1: 한 청크를 검색해 이웃과 함께 붙인다.
- RAG k=3: 세 청크를 검색해 이웃과 함께 붙인다.

각 에이전트의 품질(0~5 평균)·평균 토큰·상대 비용을 잰다. 검색을 늘리면 품질은 오르지만 토큰과
비용도 오른다. 표가 그 트레이드오프를 드러낸다. 코퍼스는 S2 RAG(RAG를 설명한 위키 문서)다.

실행:
    uv run python src/section4/lec06/benchmark.py
"""

import asyncio
import re

import litellm

from section2.lec06.mini_rag import build_messages, expand_with_neighbors, open_index, retrieve
from section3.lec02.async_llm import acomplete

COUNT_MODEL = "gemini/gemini-2.5-flash"
# 토큰당 단가(USD/100만 토큰). 입력보다 출력이 비싸다. 상대 비용 계산용 예시값.
IN_RATE, OUT_RATE = 0.075, 0.30

SCORER = "답이 기준을 얼마나 충족하는지 0에서 5까지 정수 하나로만 답하라. 5는 완벽, 0은 전혀 아님."

TESTSET = [
    {"q": "RAG란 무엇인가요?", "criteria": "LLM이 외부 정보를 검색해 통합하는 기법임을 설명한다"},
    {
        "q": "RAG라는 용어는 언제 어디서 처음 소개되었나요?",
        "criteria": "2020년 메타(Meta)의 연구 논문에서 소개되었음을 답한다",
    },
    {
        "q": "Retro 방식의 단점은 무엇인가요?",
        "criteria": "처음부터 훈련되어 높은 훈련 실행 비용이 든다는 점을 답한다",
    },
    {
        "q": "희소 벡터의 특징은 무엇인가요?",
        "criteria": "사전 길이이며 대부분 0을 포함한다는 점을 답한다",
    },
]

_COLLECTION = None


def _collection():
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = open_index()
    return _COLLECTION


def _tokens(messages: list[dict], answer: str) -> tuple[int, int]:
    in_tok = litellm.token_counter(model=COUNT_MODEL, messages=messages)
    out_tok = litellm.token_counter(model=COUNT_MODEL, text=answer)
    return in_tok, out_tok


async def _run(messages: list[dict]) -> dict:
    answer = (await acomplete(messages)).strip()
    in_tok, out_tok = _tokens(messages, answer)
    return {"answer": answer, "in": in_tok, "out": out_tok}


async def agent_model_only(question: str) -> dict:
    return await _run(
        [
            {"role": "system", "content": "질문에 아는 대로 정확히 답한다."},
            {"role": "user", "content": question},
        ]
    )


async def agent_rag(question: str, k: int) -> dict:
    contexts = expand_with_neighbors(
        _collection(),
        retrieve(_collection(), question, k),
        window=1,
    )
    return await _run(build_messages(question, contexts))


async def score(question: str, answer: str, criteria: str) -> int:
    """답이 기준을 얼마나 충족하는지 0~5로 채점한다. PASS/FAIL이 아니라 점수다."""
    verdict = await acomplete(
        [
            {"role": "system", "content": SCORER},
            {"role": "user", "content": f"질문: {question}\n기준: {criteria}\n답: {answer}"},
        ]
    )
    match = re.search(r"[0-5]", verdict)
    return int(match.group()) if match else 0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


async def benchmark(agents, testset) -> list[dict]:
    """에이전트마다 테스트셋을 돌려 품질·토큰·비용을 잰다."""
    rows = []
    for name, agent_fn in agents:
        scores, costs, tokens = [], [], []
        for case in testset:
            out = await agent_fn(case["q"])
            scores.append(await score(case["q"], out["answer"], case["criteria"]))
            tokens.append(out["in"] + out["out"])
            costs.append(out["in"] * IN_RATE + out["out"] * OUT_RATE)
        rows.append(
            {
                "name": name,
                "quality": _mean(scores),
                "tokens": _mean(tokens),
                "cost": _mean(costs),
            }
        )
    cheapest = min(r["cost"] for r in rows)
    for row in rows:
        row["rel_cost"] = row["cost"] / cheapest
    return rows


def _table(rows: list[dict]) -> None:
    print("| 에이전트 | 품질(0~5) | 평균 토큰 | 상대 비용 |")
    print("| --- | --- | --- | --- |")
    for row in rows:
        cells = f"{row['quality']:.1f} | {row['tokens']:.0f} | {row['rel_cost']:.1f}x"
        print(f"| {row['name']} | {cells} |")


AGENTS = [
    ("모델 단독", agent_model_only),
    ("RAG k=1", lambda q: agent_rag(q, 1)),
    ("RAG k=3", lambda q: agent_rag(q, 3)),
]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("=== 다중 에이전트 벤치마크 (S2 RAG 코퍼스) ===\n")
    rows = asyncio.run(benchmark(AGENTS, TESTSET))
    _table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
