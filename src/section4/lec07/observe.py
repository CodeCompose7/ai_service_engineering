"""S4 lec07 — 관찰·운영 (observe.py).

앞 단원들의 하네스는 self.trace에 스텝을 남겼다. 그건 한 요청을 들여다보는 데는 좋지만, 수천 요청이
도는 운영에서는 부족하다. 무엇이 느린지, 얼마나 실패하는지를 전체에서 봐야 한다.

관찰 모듈은 세 겹이다.

- 구조화 로그: print 한 줄 대신 JSON으로 남긴다. 기계가 검색·집계할 수 있다.
- 트레이싱: 한 요청의 스텝을 시간·성패와 함께 스팬으로 기록한다. 어디서 느렸는지 보인다.
- 메트릭: 여러 요청의 스팬을 모아 추세를 본다. p50·p95 지연, 에러율 같은 것.

가짜 sleep이 아니라 실제 AI 요청에 끼운다. S2 RAG의 검색·생성을 스팬으로 재므로, 검색은 빠르고
생성(LLM)은 느린 진짜 지연이 메트릭에 드러난다.

실행:
    uv run python src/section4/lec07/observe.py
"""

import asyncio
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass

from section2.lec06.mini_rag import build_messages, expand_with_neighbors, open_index, retrieve
from section3.lec02.async_llm import acomplete


def log_event(**fields) -> None:
    """구조화 로그 한 줄. JSON이라 grep·집계가 된다. '스텝 끝남' 같은 평문과 다르다."""
    print(json.dumps(fields, ensure_ascii=False))


@dataclass
class Span:
    """한 스텝의 이름·소요 시간(ms)·성패."""

    name: str
    ms: float
    ok: bool


class Trace:
    """한 요청의 스텝들을 시간·성패와 함께 기록한다. 누구의 어떤 요청인지도 함께 남긴다."""

    def __init__(self, request_id: str, user: str = "anonymous", session: str = "-"):
        self.request_id = request_id
        self.user = user
        self.session = session
        self.spans: list[Span] = []

    @contextmanager
    def span(self, name: str):
        """with 블록의 소요 시간을 재서 스팬으로 남기고, 구조화 로그도 찍는다."""
        start = time.perf_counter()
        ok = True
        try:
            yield
        except Exception:
            ok = False
            raise
        finally:
            ms = (time.perf_counter() - start) * 1000
            self.spans.append(Span(name, ms, ok))
            log_event(
                user=self.user,
                session=self.session,
                request=self.request_id,
                step=name,
                ms=round(ms, 1),
                ok=ok,
            )


def _percentile(values: list[float], p: int) -> float:
    """정렬한 값에서 p 분위수를 고른다. p95는 '느린 쪽 5%를 뺀 최댓값'쯤."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * p / 100))
    return ordered[index]


def metrics(traces: list[Trace]) -> dict:
    """여러 트레이스를 메트릭으로 모은다. 개별 사건이 아니라 전체 추세를 본다."""
    spans = [s for trace in traces for s in trace.spans]
    latencies = [s.ms for s in spans]
    errors = sum(1 for s in spans if not s.ok)
    return {
        "requests": len(traces),
        "spans": len(spans),
        "p50_ms": round(_percentile(latencies, 50), 1),
        "p95_ms": round(_percentile(latencies, 95), 1),
        "error_rate": round(errors / len(spans), 2) if spans else 0.0,
    }


def metrics_by_user(traces: list[Trace]) -> dict:
    """사용자별로 묶어 메트릭을 낸다. 누가 느리고 누가 실패하는지 갈라 본다."""
    by_user: dict[str, list[Trace]] = {}
    for trace in traces:
        by_user.setdefault(trace.user, []).append(trace)
    return {user: metrics(ts) for user, ts in sorted(by_user.items())}


# --- 운영: 관찰을 행동으로 ---
def check_alerts(m: dict, p95_max: float = 3000.0, error_max: float = 0.05) -> list[str]:
    """메트릭이 SLO 임계치를 넘는지 본다. 넘으면 경보 목록을, 정상이면 빈 목록을 돌려준다.

    관찰(메트릭)을 운영(행동)으로 잇는 다리다. 사람은 메트릭을 종일 보지 못하니, 임계치를 두고
    넘으면 알림이 깨운다.
    """
    alerts = []
    if m["p95_ms"] > p95_max:
        alerts.append(f"p95 지연 {m['p95_ms']}ms > {p95_max}ms")
    if m["error_rate"] > error_max:
        alerts.append(f"에러율 {m['error_rate']} > {error_max}")
    return alerts


_COLLECTION = None


def _collection():
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = open_index()
    return _COLLECTION


async def traced_rag(
    trace: Trace,
    question: str,
    must_contain: str | None = None,
) -> str:
    """관찰을 끼운 실제 RAG 요청. 검색·생성·검증을 각각 스팬으로 잰다."""
    with trace.span("retrieve"):
        contexts = expand_with_neighbors(
            _collection(),
            retrieve(_collection(), question, 3),
            1,
        )
    with trace.span("generate"):
        answer = (await acomplete(build_messages(question, contexts))).strip()
    try:
        with trace.span("validate"):
            if must_contain and must_contain not in answer:
                raise RuntimeError("출력 검증 실패")
    except RuntimeError:
        pass  # 검증 실패는 스팬에 ok=False로 남고, 처리는 이어간다
    return answer


# 누구의(user)·어느 세션(session)·어떤 요청(request)인지를 함께 남긴다.
CASES = [
    ("req-0", "alice", "sess-a", "RAG란 무엇인가요?", None),
    ("req-1", "alice", "sess-a", "Retro 방식의 단점은 무엇인가요?", None),
    ("req-2", "bob", "sess-b", "희소 벡터의 특징은 무엇인가요?", "존재하지않는단어"),
]


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    retrieve(_collection(), "워밍업", 1)  # 임베더 콜드 로드를 측정 밖으로 뺀다
    print("=== 구조화 로그 (누구의 어떤 요청인지까지 JSON 한 줄로) ===")
    traces = []
    for request_id, user, session, question, must_contain in CASES:
        trace = Trace(request_id, user=user, session=session)
        asyncio.run(traced_rag(trace, question, must_contain))
        traces.append(trace)

    print("\n=== 메트릭 (전체) ===")
    for key, value in metrics(traces).items():
        print(f"  {key}: {value}")

    by_user = metrics_by_user(traces)
    print("\n=== 사용자별 메트릭 ===")
    for user, user_metrics in by_user.items():
        print(
            f"  {user}: 요청 {user_metrics['requests']}, "
            f"p95 {user_metrics['p95_ms']}ms, 에러율 {user_metrics['error_rate']}"
        )

    print("\n=== 운영: SLO 알림 (임계치 p95<3000ms, 에러율<0.05) ===")
    for alert in check_alerts(metrics(traces)):
        print(f"  [ALERT] 전체: {alert}")
    for user, user_metrics in by_user.items():
        for alert in check_alerts(user_metrics):
            print(f"  [ALERT] {user}: {alert}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
