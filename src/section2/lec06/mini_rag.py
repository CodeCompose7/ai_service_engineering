"""lec06 — mini RAG. retrieval → generation → 출처.

lec05까지 만든 벡터DB 위에 생성과 출처 표시를 얹어 RAG 한 바퀴를 완성한다. 질문을
임베딩해 관련 청크를 검색하고(retrieval), 그 근거를 프롬프트에 넣어 LLM이 답을 쓰고
(generation), 어느 청크에서 왔는지 출처를 보여준다. 데이터는 rag.pdf다.

lec05 8절의 한계, 곧 답이 청크 경계에서 갈리는 문제를 두 가지로 다룬다.
- top-k 검색으로 갈린 조각을 함께 모은다.
- 맞은 청크의 앞뒤 이웃을 붙여(neighbor expansion) 넓은 맥락을 준다. 작게 검색하고
  크게 돌려주는 방식이다.

생성은 S1처럼 LiteLLM을 경유한다. .env의 DEFAULT_PROVIDER를 앞세우고 준비된 프로바이더로
넘어가며, 클라우드든 로컬(Ollama)이든 같은 코드로 호출한다.

실행:
    uv run python src/section2/lec06/mini_rag.py "검색 증강 생성은 어떻게 동작하나요?"
"""

import os
import sys
from pathlib import Path

from section2.lec03.chunker import chunk_text, load_document_text
from section2.lec04.embedder import embed
from section2.lec05.crud import build_index, get, make_collection, search

PERSIST_DIR = Path(__file__).parent / "data" / "chroma_db"  # .gitignore됨

DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5",
}
CLOUD_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

SYSTEM_PROMPT = (
    "너는 주어진 근거만으로 답하는 도우미다. 근거에 있는 내용으로만 한국어로 간결히 "
    "답하고, 근거에 없으면 모른다고 말한다. 답 끝에 사용한 근거 번호를 [n] 형태로 단다."
)


def open_index():
    """rag.pdf를 인덱싱한 영속 컬렉션을 연다. 비어 있으면 채운다."""
    collection = make_collection("rag_docs", persist_dir=PERSIST_DIR)
    if collection.count() == 0:
        chunks = chunk_text(load_document_text(), 500, 80)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metas = [{"source": "rag.pdf", "chunk": i} for i in range(len(chunks))]
        build_index(collection, chunks, metas, ids=ids)
    return collection


def retrieve(collection, question, k: int = 3) -> list[dict]:
    """질문을 임베딩해 가까운 청크 k개를 찾는다. top-k가 갈린 조각을 함께 모은다."""
    return search(collection, embed(question), k=k)


def expand_with_neighbors(collection, hits, window: int = 1) -> list[dict]:
    """검색된 청크의 앞뒤 window개를 붙여 맥락을 넓힌다. 작게 검색하고 크게 돌려준다.

    청크 id가 chunk_<번호>라, 이웃은 번호를 ±window 해서 가져온다. 번호 순으로 정렬해
    돌려주므로 LLM이 읽을 때 문맥이 이어진다.
    """
    indices = set()
    for hit in hits:
        center = hit["metadata"]["chunk"]
        for j in range(max(0, center - window), center + window + 1):
            indices.add(j)
    rows = get(collection, ids=[f"chunk_{j}" for j in sorted(indices)])
    rows.sort(key=lambda r: r["metadata"]["chunk"])
    return rows


def build_messages(question, contexts) -> list[dict]:
    """근거 청크와 질문으로 LLM 메시지를 만든다."""
    blocks = "\n\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(contexts))
    user = f"근거:\n{blocks}\n\n질문: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def resolve_model(env: dict | None = None) -> tuple[str, str, dict]:
    """준비된 프로바이더를 골라 (이름, 모델 문자열, 추가 인자)를 만든다. DEFAULT_PROVIDER 우선."""
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    default = env.get("DEFAULT_PROVIDER")
    order = ([default] if default in ready else []) + [n for n in ready if n != default]
    if not order:
        raise RuntimeError("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄우세요.")
    provider = order[0]
    if provider == "ollama":
        model = f"ollama/{env.get('OLLAMA_MODEL', 'gemma4:12b')}"
        return provider, model, {"api_base": env.get("OLLAMA_API_BASE")}
    return provider, DEFAULT_MODELS[provider], {}


def generate(messages) -> tuple[str, str]:
    """LiteLLM으로 답을 생성한다. (모델 이름, 답 본문)을 돌려준다."""
    import litellm

    provider, model, kwargs = resolve_model()
    resp = litellm.completion(model=model, messages=messages, **kwargs)
    return model, resp.choices[0].message.content


def answer(collection, question, k: int = 3, window: int = 1) -> dict:
    """질문에 RAG로 답한다. 검색 → 이웃 확장 → 생성 → 답·출처."""
    hits = retrieve(collection, question, k)
    contexts = expand_with_neighbors(collection, hits, window)
    model, text = generate(build_messages(question, contexts))
    return {"answer": text, "model": model, "hits": hits, "contexts": contexts}


def _preview(messages, contexts) -> None:
    """LLM에 보내는 프롬프트의 모양을 짧게 보여준다. 근거가 어떻게 주입되는지 확인용."""
    print("LLM에 보내는 프롬프트 (미리보기):")
    print(f"  [system] {messages[0]['content'][:48]}...")
    print(f"  [user] 근거 {len(contexts)}청크 + 질문")
    for i, c in enumerate(contexts[:2], 1):
        print(f"    [{i}] {c['text'][:34]}...")
    if len(contexts) > 2:
        print(f"    ... (총 {len(contexts)}청크)")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    collection = open_index()

    print("=== 1. 근거가 있는 질문 ===")
    q1 = sys.argv[1] if len(sys.argv) > 1 else "검색 증강 생성은 어떻게 동작하나요?"
    hits = retrieve(collection, q1, k=3)
    contexts = expand_with_neighbors(collection, hits, window=1)
    messages = build_messages(q1, contexts)
    print(f"질문: {q1}\n")
    _preview(messages, contexts)
    model, text = generate(messages)
    print(f"\n답 ({model}):\n{text}")
    sources = ", ".join(f"#{h['metadata']['chunk']}({h['similarity']:.2f})" for h in hits)
    print(f"출처: {sources}")

    print("\n=== 2. 근거 밖 질문 — grounding ===")
    q2 = "이 회사의 환불 정책은 어떻게 되나요?"
    result = answer(collection, q2, k=3, window=1)
    best = max(h["similarity"] for h in result["hits"])
    print(f"질문: {q2}")
    print(f"답 ({result['model']}): {result['answer']}")
    print(f"검색 최고 유사도 {best:.3f} — 낮으니 근거가 없고, 지어내지 않습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
