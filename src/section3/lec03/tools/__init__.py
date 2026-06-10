"""lec03 도구 — 위치(geocode·weather·air_quality)와 쇼핑(find_user·get_orders·get_order_detail).

도구가 여럿이라 모델은 질문에 맞는 도구를 골라 부른다(라우팅). 이름으로 도구를 찾아 await하는
run_tool과, 모델에 줄 스키마 목록 TOOLS를 모은다. 모두 async다.
"""

from section3.lec03.tools.air_quality import SCHEMA as AIR_SCHEMA
from section3.lec03.tools.air_quality import get_air_quality
from section3.lec03.tools.geocode import SCHEMA as GEO_SCHEMA
from section3.lec03.tools.geocode import geocode
from section3.lec03.tools.shop import (
    FIND_USER_SCHEMA,
    GET_ORDER_DETAIL_SCHEMA,
    GET_ORDERS_SCHEMA,
    find_user,
    get_order_detail,
    get_orders,
)
from section3.lec03.tools.weather import SCHEMA as WEATHER_SCHEMA
from section3.lec03.tools.weather import get_weather

_REGISTRY = {
    "geocode": (geocode, GEO_SCHEMA),
    "get_weather": (get_weather, WEATHER_SCHEMA),
    "get_air_quality": (get_air_quality, AIR_SCHEMA),
    "find_user": (find_user, FIND_USER_SCHEMA),
    "get_orders": (get_orders, GET_ORDERS_SCHEMA),
    "get_order_detail": (get_order_detail, GET_ORDER_DETAIL_SCHEMA),
}

TOOLS = [schema for _, schema in _REGISTRY.values()]


async def run_tool(name: str, args: dict):
    """이름으로 도구를 찾아 await한다. 모르는 도구는 막는다."""
    if name not in _REGISTRY:
        raise ValueError(f"모르는 도구: {name}")
    func, _ = _REGISTRY[name]
    return await func(**args)
