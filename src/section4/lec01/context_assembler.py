"""S4 lec01 — 컨텍스트 엔지니어링 (컨텍스트 어셈블러).

윈도우는 한정돼 있다. 무엇을 언제 넣을지가 컨텍스트 엔지니어링이다. 같은 질문도 어떤 맥락을
넣느냐로 답이 달라진다. 여기서는 토큰 예산 안에 네 가지를 조립한다.

1. 검색(retrieval): 지식 베이스에서 질문에 관련된 청크만 (S2 임베더 재사용).
2. 최근 대화(recency): 최근 몇 턴은 그대로.
3. 압축(compaction): 오래된 대화는 요약해 자리를 아낀다.
4. 질문: 늘 들어간다.

예산이 넉넉하면 오래된 대화도 그대로 넣고 청크도 많이 넣는다. 예산이 빠듯하면 compaction이 켜져
오래된 대화를 요약으로 줄이고, 그래도 넘치면 청크를 덜어낸다. 토큰은 LiteLLM token_counter로 잰다.

실행:
    uv run python src/section4/lec01/context_assembler.py
"""

import asyncio

import litellm

from section2.lec04.embedder import most_similar
from section3.lec02.async_llm import acomplete

COUNT_MODEL = "gemini/gemini-2.5-flash"
SYSTEM = "너는 도우미다. 주어진 근거와 대화 맥락만 써서 한국어로 짧게 답한다."
COMPACT_SYSTEM = "다음 대화를 한두 문장으로 요약한다. 사용자에 관한 사실만 남긴다."
RECENT_TURNS = 2  # 최근 몇 턴을 그대로 둘지


def count_tokens(text: str) -> int:
    """LiteLLM으로 토큰 수를 잰다."""
    return litellm.token_counter(model=COUNT_MODEL, text=text)


def _retrieve(question: str, kb: list[str], k: int) -> list[str]:
    """질문에 가장 가까운 청크 k개를 임베딩 유사도로 고른다."""
    return [text for text, _ in most_similar(question, kb)[:k]]


def _build_user(chunks: list[str], memory: str, recent: list[tuple], question: str) -> str:
    """네 조각을 하나의 user 메시지로 조립한다."""
    blocks = "\n".join(f"- {c}" for c in chunks) or "(없음)"
    talk = "\n".join(f"{r}: {c}" for r, c in recent) or "(없음)"
    return (
        f"[근거]\n{blocks}\n\n"
        f"[이전 대화 요약]\n{memory or '(없음)'}\n\n"
        f"[최근 대화]\n{talk}\n\n"
        f"[질문] {question}"
    )


async def _compact(old: list[tuple]) -> str:
    """오래된 대화를 한두 문장으로 압축한다."""
    convo = "\n".join(f"{r}: {c}" for r, c in old)
    return (await acomplete(
        [{"role": "system", "content": COMPACT_SYSTEM}, {"role": "user", "content": convo}]
    )).strip()


async def assemble(
    question: str, history: list[tuple], kb: list[str], budget: int, k: int = 4
) -> dict:
    """예산 안에 검색·최근 대화·압축을 조립한다. 예산이 빠듯하면 압축하고 청크를 덜어낸다."""
    chunks = _retrieve(question, kb, k)
    recent, old = history[-RECENT_TURNS:], history[:-RECENT_TURNS]
    memory_text = "\n".join(f"{r}: {c}" for r, c in old)

    # 1) 오래된 대화를 그대로 넣어 보고, 예산에 맞으면 그대로 둔다.
    user = _build_user(chunks, memory_text, recent, question)
    mode, summary = "verbatim", None

    # 2) 넘치면 오래된 대화를 요약으로 압축한다.
    if old and count_tokens(user) > budget:
        summary = await _compact(old)
        memory_text = summary
        user = _build_user(chunks, memory_text, recent, question)
        mode = "compacted"

    # 3) 그래도 넘치면 덜 관련된 청크부터 덜어낸다.
    while count_tokens(user) > budget and chunks:
        chunks = chunks[:-1]
        user = _build_user(chunks, memory_text, recent, question)

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    return {
        "messages": messages,
        "mode": mode,
        "chunks_kept": len(chunks),
        "summary": summary,
        "tokens": count_tokens(user),
        "budget": budget,
    }


# --- 데모용 지식 베이스와 대화 ---
KB = [
    "Pro 플랜은 월 2만 원이고 팀 협업 기능을 포함한다.",
    "Free 플랜은 월 0원이며 개인 사용만 가능하다.",
    "환불은 결제 후 7일 이내에 가능하다.",
    "데이터는 한국 리전 서버에 저장된다.",
    "Pro 플랜 사용자는 우선 기술 지원을 받는다.",
    "모바일 앱은 iOS와 Android 모두 지원한다.",
]
HISTORY = [
    ("user", "안녕, 나는 지금 Free 플랜을 쓰고 있어."),
    ("assistant", "네, Free 플랜을 사용 중이시군요. 무엇을 도와드릴까요?"),
    ("user", "회사 동료들이랑 같이 문서를 쓰고 싶어."),
    ("assistant", "협업이 필요하시군요. 더 알려주시면 안내해 드릴게요."),
    ("user", "비용도 너무 비싸지 않았으면 해."),
    ("assistant", "예산도 고려해서 보겠습니다."),
]
QUESTION = "팀 기능을 쓰려면 나는 어떻게 해야 해?"


def _show(label: str, result: dict) -> None:
    print(f"=== {label} (예산 {result['budget']} 토큰) ===")
    print(
        f"  조립: {result['tokens']}토큰 / 청크 {result['chunks_kept']}개 / "
        f"오래된 대화 {result['mode']}"
    )
    if result["summary"]:
        print(f"  압축 요약: {result['summary']}")
    print()


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print(f"질문: {QUESTION}\n")
    for label, budget in [("넉넉한 예산", 400), ("빠듯한 예산", 160)]:
        result = asyncio.run(assemble(QUESTION, HISTORY, KB, budget))
        _show(label, result)
    # 빠듯한 예산으로 조립한 컨텍스트로 실제 답을 만들어 본다.
    tight = asyncio.run(assemble(QUESTION, HISTORY, KB, 160))
    answer = asyncio.run(acomplete(tight["messages"]))
    print(f"빠듯한 컨텍스트로 만든 답:\n{answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
