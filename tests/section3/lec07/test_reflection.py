"""lec07 자기수정 그래프 테스트.

만족 판정과 루프 조건 엣지(route)를 본다. generate·reflect·revise의 전체 루프는 모델이 필요해
예제로 확인한다.
"""

from langgraph.graph import END

from section3.lec07.reflection import APP, _is_satisfied, route


def test_is_satisfied_on_ok():
    assert _is_satisfied("OK")
    assert _is_satisfied("  ok, 더 고칠 게 없다")


def test_not_satisfied_when_critique_present():
    assert not _is_satisfied("타입 검증이 빠졌습니다")


def test_route_revises_when_not_satisfied():
    assert route({"critique": "고칠 점 있음", "rounds": 0}) == "revise"


def test_route_ends_when_satisfied():
    assert route({"critique": "OK", "rounds": 0}) == END


def test_route_ends_at_max_rounds():
    assert route({"critique": "고칠 점 있음", "rounds": 2}) == END


def test_graph_has_reflection_nodes():
    nodes = APP.get_graph().nodes
    assert {"generate", "reflect", "revise"} <= set(nodes)
