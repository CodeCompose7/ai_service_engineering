"""S4 lec02 최소 하네스 테스트.

파싱 가드와 능력 감지 같은 순수·메타 로직을 본다. 네이티브·폴백 루프의 전체 실행은 모델이 필요해
예제로 확인한다.
"""

from section3.lec01.tools.calculator import SCHEMA as CALC_SCHEMA
from section4.lec02.harness import Harness, _dispatch


def test_parse_action_plain_json():
    assert Harness._parse_action('{"tool": "calculate", "args": {"a": 1}}') == {
        "tool": "calculate",
        "args": {"a": 1},
    }


def test_parse_action_strips_markdown_fence():
    assert Harness._parse_action('```json\n{"answer": "42"}\n```') == {"answer": "42"}


def test_parse_action_extracts_from_prose():
    raw = '네, 계산하겠습니다. {"tool": "calculate", "args": {"a": 3}} 입니다.'
    assert Harness._parse_action(raw)["tool"] == "calculate"


def test_parse_action_returns_none_on_garbage():
    assert Harness._parse_action("도구가 없습니다") is None
    assert Harness._parse_action("{깨진 json}") is None


def test_force_fallback_disables_native():
    h = Harness("gemini/gemini-2.5-flash", [CALC_SCHEMA], _dispatch, force_fallback=True)
    assert h.native is False


def test_native_detected_for_capable_model():
    h = Harness("gemini/gemini-2.5-flash", [CALC_SCHEMA], _dispatch)
    assert h.native is True


def test_fallback_system_lists_tool():
    h = Harness("ollama/llama3.2", [CALC_SCHEMA], _dispatch)
    assert h.native is False
    assert "calculate" in h._fallback_system()


def test_dispatch_runs_calculate():
    assert _dispatch("calculate", {"a": 3, "b": 4, "op": "multiply"}) == 12
