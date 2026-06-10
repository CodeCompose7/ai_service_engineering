"""lec03 도구 — 도시 이름을 좌표로 (Open-Meteo geocoding, 무료·키 없음).

라우팅·연계의 시작점이다. 날씨·미세먼지 도구는 위도·경도를 받으므로, 모델은 먼저 geocode로
도시를 좌표로 바꾸고 그 결과를 다음 도구에 넘긴다.

리턴은 dict가 아니라 Location dataclass다. 도구가 모델에 보내는 출력의 계약을 타입으로 못박는다.
에이전트가 경계에서 asdict로 JSON으로 바꿔 넘긴다.
"""

from dataclasses import dataclass

import httpx

from section3.lec03.tools.errors import ToolError

GEO = "https://geocoding-api.open-meteo.com/v1/search"


@dataclass
class Location:
    name: str
    country: str
    latitude: float
    longitude: float


async def geocode(name: str) -> Location:
    """도시 이름으로 위도·경도를 찾는다."""
    params = {"name": name, "count": 1, "language": "ko"}
    async with httpx.AsyncClient(timeout=10) as client:
        data = (await client.get(GEO, params=params)).json()
    hits = data.get("results")
    if not hits:
        raise ToolError(f"'{name}' 위치를 찾지 못했습니다.")
    r = hits[0]
    return Location(
        name=r.get("name"),
        country=r.get("country"),
        latitude=r.get("latitude"),
        longitude=r.get("longitude"),
    )


SCHEMA = {
    "type": "function",
    "function": {
        "name": "geocode",
        "description": (
            "도시나 지명을 위도·경도로 바꾼다. name은 영어로 준다. "
            "날씨나 미세먼지를 묻기 전에 먼저 불러 좌표를 얻는다."
        ),
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "도시나 지명 (영어)"}},
            "required": ["name"],
        },
    },
}
