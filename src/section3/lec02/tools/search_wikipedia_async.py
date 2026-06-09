"""lec02 비동기 위키 검색 도구 — lec01 동기 도구의 async 짝.

5.3절의 종착점이다. lec01의 search_wikipedia가 동기(httpx.get + complete)라면, 이것은 같은 일을
async로 한다. httpx.AsyncClient로 네트워크를, llm.acomplete로 요약을 await한다. 그래서 에이전트가
독립적인 검색 여러 건을 asyncio.gather로 동시에 실행할 수 있다.

lec01 도구는 lec01 강의용으로 그대로 두고, 비동기 버전은 lec02에서 따로 만든다. 모델에 줄 스키마와
상수도 여기서 독립으로 둔다. 공유하는 것은 LLM 호출(llm.acomplete)뿐이다.
"""

import urllib.parse

import httpx

from section3.lec01.llm import acomplete

WIKI = "https://en.wikipedia.org"
HEADERS = {"User-Agent": "ai-service-engineering-edu/0.1 (course example)"}
SUMMARY_SYSTEM = (
    "주어진 영어 위키백과 내용을 한국어로 두세 문장으로 번역·요약한다. "
    "주어진 내용 밖의 말은 보태지 않는다."
)


async def search_wikipedia_async(query: str) -> str:
    """위키백과에서 query를 비동기로 검색해, 내용을 요약하고 출처와 함께 돌려준다."""
    search = {
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "srlimit": 1,
    }
    async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
        hits = (await client.get(f"{WIKI}/w/api.php", params=search)).json()["query"]["search"]
        if not hits:
            return "위키백과에서 관련 문서를 찾지 못했습니다."
        title = hits[0]["title"]
        url = f"{WIKI}/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        data = (await client.get(url, follow_redirects=True)).json()
    extract = data.get("extract", "")
    page = data.get("content_urls", {}).get("desktop", {}).get("page", url)
    if not extract:
        return f"문서를 찾았지만 요약을 가져오지 못했습니다. (출처: {page})"
    summary = await acomplete(
        [
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": f"문서: {title}\n내용: {extract}"},
        ]
    )
    return f"{summary}\n(출처: {title} — {page})"


SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_wikipedia",
        "description": (
            "영문 위키백과에서 주제를 검색해 한국어 요약과 출처를 돌려준다. "
            "query는 영어 검색어로 준다. 일반 지식이나 사실을 확인할 때 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색할 주제나 키워드"}},
            "required": ["query"],
        },
    },
}
