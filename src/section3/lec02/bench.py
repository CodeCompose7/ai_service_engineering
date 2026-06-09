"""lec02 §5 — 도구 실행: 순차 → 병렬 → 비동기.

도구가 여러 번, 그것도 서로 독립으로 불릴 때(예: 위키 검색 여러 건), 어떻게 실행하느냐에 따라
걸리는 시간이 크게 달라진다. 같은 검색 묶음을 세 방식으로 돌려 벽시계 시간을 잰다.

1. 동기 순차: 하나가 끝나야 다음을 시작한다. 시간은 모두의 합이다. 단순하지만 느리다.
   지금 run_agent가 도구 호출을 처리하는 방식이 이것이다.
2. 동기 병렬(스레드): 동기 도구는 그대로 두고, 부르는 쪽만 스레드로 동시에 던진다. I/O로 기다리는
   동안 GIL을 놓아 호출이 겹친다. 도구를 고칠 필요가 없어, agent.py만 바꾸면 된다.
3. 비동기 도구: 도구 자체를 async로 바꾸고 asyncio.gather로 한꺼번에 기다린다. 도구까지 손대야
   하지만, 호출이 많아질수록 스레드보다 가볍게 확장된다.

독립적인 호출에만 통한다. 계산기처럼 직전 결과가 다음 입력이면 순서를 못 바꾼다.

실행:
    uv run python src/section3/lec02/bench.py
"""

import asyncio
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import httpx

from section3.lec01.llm import resolve_model
from section3.lec01.tools.search_wikipedia import search_wikipedia

QUERIES = ["Eiffel Tower", "Tokyo Tower", "Colosseum"]
WIKI = "https://en.wikipedia.org"
HEADERS = {"User-Agent": "ai-service-engineering-edu/0.1 (course example)"}


def run_sequential(queries: list[str]) -> list[str]:
    """동기 순차 — 하나씩 끝까지. run_agent가 지금 쓰는 방식."""
    return [search_wikipedia(q) for q in queries]


def run_threads(queries: list[str]) -> list[str]:
    """동기 병렬 — 같은 동기 도구를 스레드 풀로 동시에. 도구는 그대로다."""
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        return list(pool.map(search_wikipedia, queries))


async def search_wikipedia_async(query: str, model: str, kwargs: dict) -> str:
    """비동기 도구 — httpx.AsyncClient와 litellm.acompletion으로 await한다."""
    import litellm

    search = {
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "srlimit": 1,
    }
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        hits = (await client.get(f"{WIKI}/w/api.php", params=search)).json()["query"]["search"]
        if not hits:
            return "문서를 찾지 못했습니다."
        title = hits[0]["title"]
        url = f"{WIKI}/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        extract = (await client.get(url, follow_redirects=True)).json().get("extract", "")
    resp = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": f"두세 문장 한국어 요약: {extract}"}],
        **kwargs,
    )
    return f"{resp.choices[0].message.content}\n(출처: {title})"


async def run_async(queries: list[str]) -> list[str]:
    """비동기 — 모두 동시에 await한다."""
    model, kwargs = resolve_model()
    return await asyncio.gather(*[search_wikipedia_async(q, model, kwargs) for q in queries])


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
