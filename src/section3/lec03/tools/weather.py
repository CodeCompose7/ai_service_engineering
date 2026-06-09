"""lec03 도구 — 좌표의 현재 날씨 (Open-Meteo forecast, 무료·키 없음).

geocode가 준 위도·경도를 받아 현재 기온과 날씨 상태를 돌려준다. 미세먼지 도구와 입력이 같아
(좌표만 필요) 서로 독립적이다. 그래서 둘을 동시에 부를 수 있다.
"""

import httpx

FORECAST = "https://api.open-meteo.com/v1/forecast"
# WMO weather code를 한국어로
WMO = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "짙은 안개", 51: "약한 이슬비", 53: "이슬비", 55: "짙은 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비", 71: "약한 눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "소나기", 82: "강한 소나기", 95: "뇌우", 96: "우박 뇌우",
}


async def get_weather(latitude: float, longitude: float) -> dict:
    """위도·경도로 현재 기온과 날씨 상태를 가져온다."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        cur = (await client.get(FORECAST, params=params)).json().get("current", {})
    code = cur.get("weather_code")
    return {"temperature_c": cur.get("temperature_2m"), "condition": WMO.get(code, f"코드 {code}")}


SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "위도·경도로 현재 기온과 날씨를 가져온다. geocode로 좌표를 먼저 얻어 넘긴다."
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
