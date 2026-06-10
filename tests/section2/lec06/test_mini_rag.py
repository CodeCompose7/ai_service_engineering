"""lec06 mini RAG의 순수 로직 테스트.

이웃 확장·프롬프트 조립·프로바이더 해석을 가짜 임베딩과 가짜 env로 검증한다. 실제
임베딩(bge-m3)과 LLM 생성은 무겁고 외부에 의존하므로 예제 실행으로 확인한다.
"""

import pytest

from section2.lec05.crud import index, make_collection
from section2.lec06.mini_rag import build_messages, expand_with_neighbors, resolve_model


def _collection_with_chunks(name, n=5):
    col = make_collection(name)
    index(
        col,
        [f"청크{i}" for i in range(n)],
        [[float(i), 0.0] for i in range(n)],
        metadatas=[{"source": "rag.pdf", "chunk": i} for i in range(n)],
        ids=[f"chunk_{i}" for i in range(n)],
    )
    return col


def test_expand_adds_adjacent_chunks():
    col = _collection_with_chunks("expand_adj")
    rows = expand_with_neighbors(col, [{"metadata": {"chunk": 2}}], window=1)
    assert [r["metadata"]["chunk"] for r in rows] == [1, 2, 3]


def test_expand_clamps_at_edge():
    col = _collection_with_chunks("expand_edge")
    rows = expand_with_neighbors(col, [{"metadata": {"chunk": 0}}], window=1)
    assert [r["metadata"]["chunk"] for r in rows] == [0, 1]  # -1은 없음


def test_expand_dedupes_overlapping_windows():
    col = _collection_with_chunks("expand_dedup")
    hits = [{"metadata": {"chunk": 1}}, {"metadata": {"chunk": 2}}]
    rows = expand_with_neighbors(col, hits, window=1)
    assert [r["metadata"]["chunk"] for r in rows] == [0, 1, 2, 3]  # 겹치는 이웃은 한 번만


def test_build_messages_numbers_contexts_and_includes_question():
    msgs = build_messages("질문?", [{"text": "근거A"}, {"text": "근거B"}])
    assert msgs[0]["role"] == "system"
    user = msgs[1]["content"]
    assert "[1] 근거A" in user
    assert "[2] 근거B" in user
    assert "질문?" in user


def test_resolve_model_prefers_default_provider():
    env = {"DEFAULT_PROVIDER": "openai", "GEMINI_API_KEY": "x", "OPENAI_API_KEY": "y"}
    provider, model, _ = resolve_model(env)
    assert provider == "openai"
    assert model == "openai/gpt-4o-mini"


def test_resolve_model_ollama():
    env = {
        "DEFAULT_PROVIDER": "ollama",
        "OLLAMA_API_BASE": "http://x",
        "OLLAMA_MODEL": "gemma4:12b",
    }
    provider, model, kwargs = resolve_model(env)
    assert provider == "ollama"
    assert model == "ollama/gemma4:12b"
    assert kwargs["api_base"] == "http://x"


def test_resolve_model_raises_when_none_ready():
    with pytest.raises(RuntimeError):
        resolve_model({})
