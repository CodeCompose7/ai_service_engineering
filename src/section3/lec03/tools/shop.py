"""lec03 도구 — 목 쇼핑 데이터 (네트워크 없이 결정적).

날씨 도구와 도메인이 다르다. 모델은 질문에 따라 위치 도구와 쇼핑 도구 사이를 라우팅한다.
쇼핑 쪽은 깊은 연계를 보인다. find_user로 사용자 id를 얻고, get_orders로 주문 목록을, 그중 한
주문을 get_order_detail로 펼친다. 앞 도구의 결과가 다음 도구의 입력이라 순서를 바꿀 수 없다.

실제 서비스라면 DB나 API를 부르겠지만, 여기서는 라우팅·연계에 집중하려고 사전을 쓴다. 그래서
세 함수는 await할 I/O가 없지만, 도구 인터페이스를 맞추려고 async로 둔다. 리턴은 dict가 아니라
dataclass다. 없는 사용자·주문은 ToolError로 올린다.
"""

from dataclasses import dataclass

from section3.lec03.tools.errors import ToolError

_USERS = {"alice": "U001", "bob": "U002", "철수": "U003"}
_ORDERS = {
    "U001": [{"order_id": "O100", "item": "노트북"}, {"order_id": "O101", "item": "마우스"}],
    "U002": [{"order_id": "O200", "item": "키보드"}],
    "U003": [{"order_id": "O300", "item": "모니터"}],
}
_DETAILS = {
    "O100": {"item": "노트북", "price": 1450000, "status": "배송 완료"},
    "O101": {"item": "마우스", "price": 39000, "status": "배송 중"},
    "O200": {"item": "키보드", "price": 89000, "status": "결제 완료"},
    "O300": {"item": "모니터", "price": 320000, "status": "배송 완료"},
}


@dataclass
class User:
    user_id: str


@dataclass
class Order:
    order_id: str
    item: str


@dataclass
class OrderList:
    orders: list[Order]


@dataclass
class OrderDetail:
    item: str
    price: int
    status: str


async def find_user(name: str) -> User:
    """사용자 이름으로 사용자 id를 찾는다. 주문 조회의 첫 단계."""
    uid = _USERS.get(name) or _USERS.get(name.lower())
    if not uid:
        raise ToolError(f"'{name}' 사용자를 찾지 못했습니다.")
    return User(user_id=uid)


async def get_orders(user_id: str) -> OrderList:
    """사용자 id로 주문 목록을 가져온다. find_user의 결과를 받는다."""
    return OrderList(orders=[Order(**row) for row in _ORDERS.get(user_id, [])])


async def get_order_detail(order_id: str) -> OrderDetail:
    """주문 id로 상세를 펼친다. get_orders가 준 주문 중 하나를 받는다."""
    detail = _DETAILS.get(order_id)
    if not detail:
        raise ToolError(f"주문 {order_id}를 찾지 못했습니다.")
    return OrderDetail(**detail)


FIND_USER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_user",
        "description": "사용자 이름으로 사용자 id를 찾는다. 주문을 조회하기 전에 먼저 부른다.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "사용자 이름"}},
            "required": ["name"],
        },
    },
}
GET_ORDERS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_orders",
        "description": "사용자 id로 주문 목록을 가져온다. find_user로 id를 먼저 얻어 넘긴다.",
        "parameters": {
            "type": "object",
            "properties": {"user_id": {"type": "string", "description": "사용자 id"}},
            "required": ["user_id"],
        },
    },
}
GET_ORDER_DETAIL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_order_detail",
        "description": "주문 id로 가격·상태 등 상세를 가져온다. get_orders가 준 주문 id를 넘긴다.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "주문 id"}},
            "required": ["order_id"],
        },
    },
}
