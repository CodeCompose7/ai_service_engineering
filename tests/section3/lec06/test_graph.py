"""lec06 LangGraph 실전 테스트.

분기·루프를 정하는 route와 표 포맷팅을 본다. route는 라이브 날씨와 무관하게 세 갈래(루프/주의/
정상)를 결정론으로 검증한다. 도구를 부르는 fetch_one과 전체 실행은 예제로 확인한다.
"""

from section3.lec06.graph import APP, _as_text, route


def test_route_loops_when_cities_remain():
    assert route({"cities": ["a", "b"], "index": 1, "reports": []}) == "fetch_one"


def test_route_branches_to_alert_on_warning():
    state = {"cities": ["a"], "index": 1, "reports": [{"warn": True}]}
    assert route(state) == "summarize_alert"


def test_route_branches_to_normal_without_warning():
    state = {"cities": ["a"], "index": 1, "reports": [{"warn": False}]}
    assert route(state) == "summarize_normal"


def test_as_text_marks_warning():
    text = _as_text([{"city": "London", "temp_c": 18, "condition": "비", "warn": True}])
    assert "(주의)" in text


def test_graph_has_loop_and_branch_nodes():
    nodes = APP.get_graph().nodes
    assert "fetch_one" in nodes
    assert "summarize_alert" in nodes
    assert "summarize_normal" in nodes
