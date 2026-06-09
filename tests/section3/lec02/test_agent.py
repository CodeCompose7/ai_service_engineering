"""lec02 단일 도구 에이전트 테스트.

각 에이전트가 도구 하나만 쓰는지, 디스패처가 도구를 실행하는지 검증한다. 도구를 반복
호출하는 run_agent 루프는 모델이 필요해 예제 실행으로 확인한다.
"""

from section3.lec02.agent import CALC_SCHEMA, WIKI_SCHEMA, _calc_dispatch


def test_each_agent_uses_one_tool():
    assert CALC_SCHEMA["function"]["name"] == "calculate"
    assert WIKI_SCHEMA["function"]["name"] == "search_wikipedia"


def test_calc_dispatch_runs_calculate():
    assert _calc_dispatch("calculate", {"a": 12, "b": 8, "op": "add"}) == 20
    assert _calc_dispatch("anything", {"a": 6, "b": 2, "op": "divide"}) == 3
