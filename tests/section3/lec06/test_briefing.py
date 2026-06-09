"""lec06 진화형 그래프 테스트.

Send fan-out과 승인 후 갈래 결정 같은 순수 로직을 본다. 병렬 수집·재시도·중단/재개의 전체
실행은 모델·네트워크가 필요해 예제로 확인한다.
"""

from langgraph.types import Send

from section3.lec06.briefing import BRIEFING, after_approval, dispatch, skipped


def test_dispatch_fans_out_one_send_per_city():
    sends = dispatch({"cities": ["A", "B", "C"]})
    assert len(sends) == 3
    assert all(isinstance(s, Send) and s.node == "city_flow" for s in sends)


def test_after_approval_skips_when_rejected():
    assert after_approval({"approved": False, "reports": [{"warn": True}]}) == "skipped"


def test_after_approval_alerts_when_warned():
    assert after_approval({"approved": True, "reports": [{"warn": True}]}) == "summarize_alert"


def test_after_approval_normal_when_calm():
    assert after_approval({"approved": True, "reports": [{"warn": False}]}) == "summarize_normal"


def test_skipped_sets_cancel_summary():
    assert "취소" in skipped({})["summary"]


def test_graph_has_subgraph_and_approval_nodes():
    nodes = BRIEFING.get_graph().nodes
    assert "city_flow" in nodes
    assert "approval" in nodes
