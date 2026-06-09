"""lec02 5절 — 도구 실행: 순차 → 병렬 → 비동기.

도구가 여러 번, 그것도 서로 독립으로 불릴 때(예: 위키 검색 여러 건), 어떻게 실행하느냐에 따라
걸리는 시간이 크게 달라진다. 같은 검색 묶음을 세 방식으로 돌려 벽시계 시간을 잰다.

1. 동기 순차: 하나가 끝나야 다음을 시작한다. 시간은 모두의 합이다. 단순하지만 느리다.
   지금 run_agent가 도구 호출을 처리하는 방식이 이것이다.
2. 동기 병렬(스레드): 동기 도구는 그대로 두고, 부르는 쪽만 스레드로 동시에 던진다. I/O로 기다리는
   동안 GIL을 놓아 호출이 겹친다. 도구를 고칠 필요가 없어, agent.py만 바꾸면 된다.
3. 비동기 도구: 도구 자체를 async로 바꾸고 asyncio.gather로 한꺼번에 기다린다.

동기 도구는 lec01의 search_wikipedia를, 비동기 도구는 lec02/tools의 async 짝을 쓴다. 같은 일을
하므로 비교가 공정하다. 독립적인 호출에만 통한다. 계산기처럼 직전 결과가 다음 입력이면 순서를 못
바꾼다.

실행:
    uv run python src/section3/lec02/bench.py
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from section3.lec01.tools.search_wikipedia import search_wikipedia
from section3.lec02.tools import search_wikipedia_async

QUERIES = ["Eiffel Tower", "Tokyo Tower", "Colosseum"]


def run_sequential(queries: list[str]) -> list[str]:
    """동기 순차 — 하나씩 끝까지. run_agent가 지금 쓰는 방식."""
    return [search_wikipedia(q) for q in queries]


def run_threads(queries: list[str]) -> list[str]:
    """동기 병렬 — 같은 동기 도구를 스레드 풀로 동시에. 도구는 그대로다."""
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        return list(pool.map(search_wikipedia, queries))


async def run_async(queries: list[str]) -> list[str]:
    """비동기 — async 도구를 모두 동시에 await한다."""
    return await asyncio.gather(*[search_wikipedia_async(q) for q in queries])


def _timed(label: str, fn) -> None:
    start = time.perf_counter()
    fn()
    print(f"  {label:<22}: {time.perf_counter() - start:.1f}s")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print(f"위키 검색 {len(QUERIES)}건({', '.join(QUERIES)})을 세 방식으로:")
    _timed("1. 동기 순차", lambda: run_sequential(QUERIES))
    _timed("2. 동기 병렬(스레드)", lambda: run_threads(QUERIES))
    _timed("3. 비동기(gather)", lambda: asyncio.run(run_async(QUERIES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
