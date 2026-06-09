"""lec03 도구 — 좌표의 현재 미세먼지 (Open-Meteo air-quality, 무료·키 없음).

날씨 도구와 마찬가지로 좌표만 받는다. 두 도구는 서로의 결과가 필요 없어 독립적이므로, 한 도시의
날씨와 미세먼지를 동시에 물어볼 수 있다.
"""

import httpx

AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _grade(pm: float) -> str:
    """pm2.5 농도를 한국 기준 등급으로."""
    if pm < 16:
        return "좋음"
    if pm < 36:
        return "보통"
    if pm < 76:
        return "나쁨"
    return "매우 나쁨"


async def get_air_quality(latitude: float, longitude: float) -> dict:
    """위도·경도로 현재 초미세먼지(pm2.5) 농도와 등급을 가져온다."""
    params = {"latitude": latitude, "longitude": longitude, "current": "pm2_5"}
    async with httpx.AsyncClient(timeout=10) as client:
        cur = (await client.get(AIR, params=params)).json().get("current", {})
    pm = cur.get("pm2_5")
    if pm is None:
        return {"error": "미세먼지 정보를 가져오지 못했습니다."}
    return {"pm2_5": pm, "grade": _grade(pm)}


SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_air_quality",
        "description": (
            "위도·경도로 현재 초미세먼지(pm2.5)와 등급을 가져온다. "
            "geocode로 좌표를 먼저 얻어 넘긴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "위도"},
                "longitude": {"type": "number", "description": "경도"},
            },
            "required": ["latitude", "longitude"],
        },
    },
}
