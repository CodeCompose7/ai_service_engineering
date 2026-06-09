"""lec07 계획 수립 그래프 테스트.

계획 파싱과 단계 루프 조건 엣지(route)를 본다. planner·executor·synthesize의 전체 실행은 모델이
필요해 예제로 확인한다.
"""

from section3.lec07.plan_execute import APP, _parse_plan, route


def test_parse_plan_strips_bullets_and_numbers():
    text = "1. 첫 단계\n- 둘째 단계\n• 셋째 단계\n\n   "
    assert _parse_plan(text) == ["첫 단계", "둘째 단계", "셋째 단계"]


def test_parse_plan_keeps_content_numbers():
    assert _parse_plan("3가지 이유를 든다") == ["3가지 이유를 든다"]


def test_route_loops_while_steps_remain():
    assert route({"plan": ["a", "b"], "step": 1}) == "executor"


def test_route_synthesizes_when_done():
    assert route({"plan": ["a", "b"], "step": 2}) == "synthesize"


def test_graph_has_plan_execute_nodes():
    nodes = APP.get_graph().nodes
    assert {"planner", "executor", "synthesize"} <= set(nodes)
