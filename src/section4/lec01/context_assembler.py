"""S4 lec01 — 컨텍스트 엔지니어링 (컨텍스트 어셈블러).

윈도우는 한정돼 있다. 무엇을 어디에 어떻게 넣을지가 컨텍스트 엔지니어링이다. 같은 질문도 어떤
맥락을 어떻게 넣느냐로 답이 달라진다. 옛 16MB 램 시절 메모리 최적화와 같은 결의 일이다.

- 무엇을: 검색(질문에 관련된 청크만)·최근 우선(가까운 대화만 그대로)·압축(오래된 대화는 줄여서).
- 어디에: 순서. 모델은 양 끝을 더 잘 보므로 관련 높은 것을 앞뒤 끝에 둔다(lost-in-the-middle).
- 어떻게 줄이나: 압축의 갈래. 잘라내기(truncate)·발췌(extractive)·요약(summarize)을 고른다.
- 어떻게 담나: 포맷. [근거]·[질문] 같은 구분자로 모델이 파싱하기 쉽게 둔다.

토큰은 LiteLLM token_counter로, 검색은 S2 임베더로 한다.

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


def _turns_text(turns: list[tuple]) -> str:
    return "\n".join(f"{r}: {c}" for r, c in turns)


# --- 검색과 순서(positioning) ---
def _retrieve(question: str, kb: list[str], k: int) -> list[str]:
    """질문에 가까운 청크 k개를 임베딩 유사도 내림차순으로 고른다."""
    return [text for text, _ in most_similar(question, kb)[:k]]


def _order_edges(items: list[str]) -> list[str]:
    """관련 높은 것을 양 끝에 둔다. 모델이 가운데를 흘려보기 때문이다(lost-in-the-middle).

    items는 관련도 내림차순. [A, B, C, D] → [A, C, D, B]로 상위 둘을 앞뒤 끝으로 보낸다.
    """
    return items[0::2] + items[1::2][::-1]


# --- 압축의 갈래(compaction) ---
def _truncate(old: list[tuple], keep: int) -> str:
    """잘라내기 — 최근 old 턴 keep개만 남기고 버린다. 공짜·즉시, 오래된 것은 잃는다."""
    return _turns_text(old[-keep:])


def _extractive(old: list[tuple], question: str, keep: int) -> str:
    """발췌 — 질문에 관련된 old 턴 keep개를 그대로 남긴다. LLM 없이 임베딩으로 고른다."""
    turns = [_turns_text([t]) for t in old]
    return "\n".join(t for t, _ in most_similar(question, turns)[:keep])


async def _summarize(old: list[tuple]) -> str:
    """요약 — LLM으로 한두 문장 압축. 비용은 들지만 전체 맥락을 담는다."""
    msgs = [
        {"role": "system", "content": COMPACT_SYSTEM},
        {"role": "user", "content": _turns_text(old)},
    ]
    return (await acomplete(msgs)).strip()


async def compact_old(old: list[tuple], strategy: str, question: str, keep: int = 2) -> str:
    """오래된 대화를 고른 전략으로 압축한다."""
    if strategy == "truncate":
        return _truncate(old, keep)
    if strategy == "extractive":
        return _extractive(old, question, keep)
    return await _summarize(old)


def _build_user(chunks: list[str], memory: str, recent: list[tuple], question: str) -> str:
    """네 조각을 구분자로 묶어 하나의 user 메시지로 조립한다. 청크는 관련 높은 것을 양 끝에 둔다."""
    blocks = "\n".join(f"- {c}" for c in _order_edges(chunks)) or "(없음)"
    return (
        f"[근거]\n{blocks}\n\n"
        f"[이전 대화]\n{memory or '(없음)'}\n\n"
        f"[최근 대화]\n{_turns_text(recent) or '(없음)'}\n\n"
        f"[질문] {question}"
    )


async def assemble(
    question: str,
    history: list[tuple],
    kb: list[str],
    budget: int,
    k: int = 4,
    strategy: str = "summarize",
) -> dict:
    """예산 안에 검색·최근 대화·압축을 조립한다. 예산이 빠듯하면 압축하고 청크를 덜어낸다."""
    chunks = _retrieve(question, kb, k)
    recent, old = history[-RECENT_TURNS:], history[:-RECENT_TURNS]
    memory_text = _turns_text(old)

    user = _build_user(chunks, memory_text, recent, question)
    mode = "verbatim"

    if old and count_tokens(user) > budget:
        memory_text = await compact_old(old, strategy, question)
        user = _build_user(chunks, memory_text, recent, question)
        mode = strategy

    while count_tokens(user) > budget and chunks:
        chunks = chunks[:-1]
        user = _build_user(chunks, memory_text, recent, question)

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    return {
        "messages": messages,
        "mode": mode,
        "chunks_kept": len(chunks),
        "tokens": count_tokens(user),
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
    ("user", "그 전에, 결제 영수증도 받을 수 있어?"),
    ("assistant", "네, 설정에서 영수증을 받으실 수 있습니다."),
    ("user", "비용도 너무 비싸지 않았으면 해."),
    ("assistant", "예산도 고려해서 보겠습니다."),
]
QUESTION = "팀 기능을 쓰려면 나는 어떻게 해야 해?"


async def _demo(label: str, budget: int) -> None:
    """한 예산으로 조립해, 실제 전송되는 컨텍스트와 그 답을 함께 보인다."""
    result = await assemble(QUESTION, HISTORY, KB, budget)
    print(f"=== {label} (예산 {budget} 토큰) ===")
    print(
        f"  조립: {result['tokens']}토큰 / 청크 {result['chunks_kept']}개 / "
        f"오래된 대화 {result['mode']}"
    )
    print("  --- 실제 전송 컨텍스트 ---")
    for line in result["messages"][1]["content"].splitlines():
        print(f"  {line}")
    answer = await acomplete(result["messages"])
    print(f"  --- 답 ---\n  {answer.strip()}\n")


async def compare_compaction() -> None:
    """오래된 대화를 세 가지 압축 전략으로 줄여 비교한다."""
    old = HISTORY[:-RECENT_TURNS]
    print(f"=== 압축의 갈래 (오래된 대화 {len(old)}턴) ===")
    strategies = [("truncate", "LLM 0회"), ("extractive", "LLM 0회"), ("summarize", "LLM 1회")]
    for strategy, cost in strategies:
        text = await compact_old(old, strategy, QUESTION)
        flat = text.replace("\n", " / ")
        print(f"  [{strategy:>10}] {count_tokens(text):>3}토큰 · {cost} → {flat}")
    print()


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print(f"질문: {QUESTION}\n")
    asyncio.run(_demo("넉넉한 예산", 400))
    asyncio.run(_demo("빠듯한 예산", 200))
    asyncio.run(compare_compaction())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
