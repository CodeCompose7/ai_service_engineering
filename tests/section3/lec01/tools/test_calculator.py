"""calculator 도구 테스트."""

from section3.lec01.tools.calculator import calculate


def test_calculate_four_ops():
    assert calculate(6, 3, "add") == 9
    assert calculate(6, 3, "subtract") == 3
    assert calculate(6, 3, "multiply") == 18
    assert calculate(6, 3, "divide") == 2


def test_calculate_divide_by_zero_is_none():
    assert calculate(1, 0, "divide") is None
