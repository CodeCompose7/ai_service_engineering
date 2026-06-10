"""S5 lec02 — 통합 어시스턴트 (assistant.py).

지금까지 만든 것을 하나로 엮는다. 한 번의 채팅 요청이 가드·검색·생성·관찰을 차례로 거친다.

- 입력 가드: 주입 방어(S4 lec04)와 욕설 검열(S4 lec02). 설정으로 켜고 끈다.
- 검색: RAG(S2 mini_rag retrieve)로 근거를 모은다. 설정으로 끄면 모델 단독으로 답한다.
- 생성: LiteLLM(S3 acomplete)로 답을 만든다.
- 출력 가드: PII 가림(S4 lec03 redact_pii).
- 관찰: 매 요청을 Trace(S4 lec07)로 스텝마다 재서 Store에 모은다. 관리자 페이지가 그걸 본다.

handle 하나가 이 파이프라인이다. app.py의 /chat 핸들러가 이걸 부른다.
"""

import asyncio
from dataclasses import dataclass

import litellm

from section2.lec06.mini_rag import build_messages, expand_with_neighbors, retrieve
from section3.lec01.llm import resolve_model
from section3.lec02.async_llm import acomplete
from section4.lec02.harness3 import llm_moderate
from section4.lec03.guard import redact_pii
from section4.lec04.injection import detect_injection
from section4.lec07.observe import Trace, metrics


@dataclass
class Settings:
    """런타임 설정. 관리자 페이지에서 토글한다."""

    guard_injection: bool = True  # 주입 방어
    moderate: bool = True  # 욕설 검열
    redact: bool = True  # 출력 PII 가림
    rag: bool = True  # RAG 검색 사용


class Store:
    """관찰 기록 보관소. 트레이스를 모아 메트릭을 낸다. 요청 id도 발급한다."""

    def __init__(self):
        self.traces: list[Trace] = []
        self._counter = 0

    def next_request_id(self) -> str:
        request_id = f"req-{self._counter}"
        self._counter += 1
        return request_id

    def add(self, trace: Trace) -> None:
        self.traces.append(trace)

    def snapshot(self) -> dict:
        return metrics(self.traces)


async def _input_blocked(message: str, settings: Settings) -> str | None:
    """입력 가드. 막을 이유가 있으면 사유를, 없으면 None을 돌려준다.

    주입·검열은 각각 LLM 호출이라 순차로 하면 느리다. 함께 돌려(gather) 가드 지연을 절반으로
    줄인다. 첫 토큰 전에 끝나야 하므로 빠를수록 좋다.
    """
    checks = []
    if settings.guard_injection:
        checks.append(("프롬프트 주입이 의심됩니다", detect_injection(message)))
    if settings.moderate:
        checks.append(("부적절한 표현이 감지되었습니다", llm_moderate(message)))
    if not checks:
        return None
    flags = await asyncio.gather(*(coro for _, coro in checks))
    for (reason, _), flagged in zip(checks, flags, strict=True):
        if flagged:
            return reason
    return None


async def handle(
    message: str,
    user: str,
    settings: Settings,
    store: Store,
    collection,
) -> dict:
    """채팅 한 번을 처리한다. 가드·검색·생성·관찰을 한 트레이스에 담는다."""
    trace = Trace(store.next_request_id(), user=user)

    with trace.span("guard"):
        reason = await _input_blocked(message, settings)
    if reason:
        store.add(trace)
        return {"blocked": True, "reason": reason, "answer": ""}

    with trace.span("retrieve"):
        if settings.rag and collection is not None:
            hits = retrieve(collection, message, 3)
            contexts = expand_with_neighbors(collection, hits, 1)
        else:
            contexts = []

    with trace.span("generate"):
        if contexts:
            messages = build_messages(message, contexts)
        else:
            messages = [{"role": "user", "content": message}]
        answer = (await acomplete(messages)).strip()

    if settings.redact:
        answer = redact_pii(answer)

    store.add(trace)
    return {"blocked": False, "reason": "", "answer": answer}


async def _generate_stream(messages: list[dict]):
    """생성을 토큰 단위로 흘린다. lec01에서 본 LiteLLM stream=True 그대로다.

    gemini-2.5-flash는 기본적으로 답하기 전에 '생각'을 해서 첫 토큰이 한참 늦다. 채팅은
    응답성이 중요하니 thinking을 꺼(budget 0) 첫 토큰을 앞당긴다. 스트리밍이 체감되려면
    첫 토큰이 빨라야 한다.
    """
    model, kwargs = resolve_model()
    extra = {}
    if model.startswith("gemini"):
        extra["thinking"] = {"type": "enabled", "budget_tokens": 0}
    stream = await litellm.acompletion(
        model=model, messages=messages, stream=True, **kwargs, **extra
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def handle_stream(
    message: str,
    user: str,
    settings: Settings,
    store: Store,
    collection,
):
    """채팅을 스트리밍으로 처리한다. 입력 가드는 스트림 전에 끝내고, 생성만 토큰 단위로 흘린다.

    출력 PII 가림은 전체 답이 있어야 하므로 스트리밍과 상충한다. 여기서는 입력 가드(주입·검열)만
    걸고, 엄격한 출력 가림이 필요하면 비스트리밍 handle을 쓴다.
    """
    trace = Trace(store.next_request_id(), user=user)

    with trace.span("guard"):
        reason = await _input_blocked(message, settings)
    if reason:
        store.add(trace)
        yield f"[차단] {reason}"
        return

    with trace.span("retrieve"):
        if settings.rag and collection is not None:
            hits = retrieve(collection, message, 3)
            contexts = expand_with_neighbors(collection, hits, 1)
        else:
            contexts = []

    with trace.span("generate"):
        if contexts:
            messages = build_messages(message, contexts)
        else:
            messages = [{"role": "user", "content": message}]
        async for token in _generate_stream(messages):
            yield token

    store.add(trace)
