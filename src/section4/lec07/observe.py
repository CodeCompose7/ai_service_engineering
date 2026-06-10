"""S4 lec07 — 관찰·운영 (observe.py).

앞 단원들의 하네스는 self.trace에 스텝을 남겼다. 그건 한 요청을 들여다보는 데는 좋지만, 수천 요청이
도는 운영에서는 부족하다. 무엇이 느린지, 얼마나 실패하는지를 전체에서 봐야 한다.

관찰 모듈은 세 겹이다.

- 구조화 로그: print 한 줄 대신 JSON으로 남긴다. 기계가 검색·집계할 수 있다.
- 트레이싱: 한 요청의 스텝을 시간·성패와 함께 스팬으로 기록한다. 어디서 느렸는지 보인다.
- 메트릭: 여러 요청의 스팬을 모아 추세를 본다. p50·p95 지연, 에러율 같은 것.

개별 로그는 한 사건을, 메트릭은 전체 건강을 본다. 운영은 둘 다 본다.

실행:
    uv run python src/section4/lec07/observe.py
"""

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass


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
    """한 요청의 스텝들을 시간·성패와 함께 기록한다."""

    def __init__(self, request_id: str):
        self.request_id = request_id
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
            log_event(request=self.request_id, step=name, ms=round(ms, 1), ok=ok)


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


def _handle(request_id: str, fail: bool = False) -> Trace:
    """관찰을 끼운 가짜 요청 처리. 검색·생성 스텝을 스팬으로 잰다."""
    trace = Trace(request_id)
    with trace.span("retrieve"):
        time.sleep(0.01)
    try:
        with trace.span("generate"):
            time.sleep(0.02)
            if fail:
                raise RuntimeError("생성 실패")
    except RuntimeError:
        pass  # 실패는 스팬에 ok=False로 남고, 처리는 이어간다
    return trace


def main() -> int:
    print("=== 구조화 로그 (요청마다 스텝을 JSON 한 줄로) ===")
    traces = [_handle(f"req-{i}", fail=(i == 3)) for i in range(5)]

    print("\n=== 메트릭 (5개 요청을 모아서) ===")
    for key, value in metrics(traces).items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
