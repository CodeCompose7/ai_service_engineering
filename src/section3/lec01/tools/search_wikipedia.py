"""위키백과 검색 도구 — 검색어로 위키백과를 찾아 출처와 함께 요약한다.

모델이 search_wikipedia(query=...)로 부르면(어떤 단어로 검색할지는 모델이 function calling으로
정한다), 이 도구가 위키백과를 검색해 문서 요약을 가져오고, 그 내용을 LiteLLM으로 두세 문장으로
정리해 출처와 함께 돌려준다. 도구가 안에서 다시 LLM을 부르는, 한 단계 똑똑한 도구다.
"""

import urllib.parse

import httpx

from section3.lec01.llm import complete

WIKI = "https://ko.wikipedia.org"
HEADERS = {"User-Agent": "ai-service-engineering-edu/0.1 (course example)"}
SUMMARY_SYSTEM = (
    "주어진 위키백과 내용을 두세 문장으로 한국어로 요약한다. 주어진 내용 밖의 말은 보태지 않는다."
)


def _search_title(query: str) -> str | None:
    """검색어로 가장 관련 있는 위키백과 문서 제목을 찾는다."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": 1,
    }
    res = httpx.get(f"{WIKI}/w/api.php", params=params, headers=HEADERS, timeout=10)
    hits = res.json()["query"]["search"]
    return hits[0]["title"] if hits else None


def _fetch_summary(title: str) -> tuple[str, str]:
    """문서 제목으로 요약(extract)과 출처 URL을 가져온다."""
    url = f"{WIKI}/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    data = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True).json()
    page = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    return data.get("extract", ""), page


def search_wikipedia(query: str) -> str:
    """위키백과에서 query를 검색해, 내용을 LiteLLM으로 요약하고 출처와 함께 돌려준다."""
    title = _search_title(query)
    if not title:
        return "위키백과에서 관련 문서를 찾지 못했습니다."
    extract, url = _fetch_summary(title)
    if not extract:
        return f"문서를 찾았지만 요약을 가져오지 못했습니다. (출처: {url})"
    summary = complete(
        [
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": f"문서: {title}\n내용: {extract}"},
        ]
    )
    return f"{summary}\n(출처: {title} — {url})"


SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_wikipedia",
        "description": (
            "위키백과에서 주제를 검색해 요약과 출처를 돌려준다. "
            "일반 지식이나 사실을 확인할 때 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색할 주제나 키워드"}},
            "required": ["query"],
        },
    },
}
