"""lec03 목 쇼핑 도구 테스트. 결정적이라 연계 체인과 dataclass 리턴을 그대로 검증한다."""

import asyncio

import pytest

from section3.lec03.tools.errors import ToolError
from section3.lec03.tools.shop import OrderDetail, User, find_user, get_order_detail, get_orders


def test_find_user_known():
    assert asyncio.run(find_user("alice")) == User(user_id="U001")


def test_find_user_unknown_raises():
    with pytest.raises(ToolError):
        asyncio.run(find_user("nobody"))


def test_chain_user_to_detail():
    uid = asyncio.run(find_user("철수")).user_id
    orders = asyncio.run(get_orders(uid)).orders
    assert orders[0].order_id == "O300"
    detail = asyncio.run(get_order_detail("O300"))
    assert detail == OrderDetail(item="모니터", price=320000, status="배송 완료")
