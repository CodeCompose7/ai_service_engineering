"""S4 lec07 관찰 모듈 테스트.

분위수와 메트릭 집계를 결정적으로 본다. 타이밍·로그는 예제로 확인한다.
"""

from section4.lec07.observe import Span, Trace, _percentile, metrics, metrics_by_user


def test_percentile():
    assert _percentile([10, 20, 30, 40], 50) == 30
    assert _percentile([], 50) == 0.0


def test_metrics_aggregates_spans():
    t1 = Trace("a")
    t1.spans = [Span("x", 10.0, True), Span("y", 20.0, False)]
    t2 = Trace("b")
    t2.spans = [Span("x", 30.0, True)]
    m = metrics([t1, t2])
    assert m["requests"] == 2
    assert m["spans"] == 3
    assert m["error_rate"] == round(1 / 3, 2)
    assert m["p50_ms"] == _percentile([10.0, 20.0, 30.0], 50)


def test_metrics_by_user_groups():
    a1 = Trace("r1", user="alice")
    a1.spans = [Span("x", 10.0, True)]
    a2 = Trace("r2", user="alice")
    a2.spans = [Span("x", 20.0, True)]
    b1 = Trace("r3", user="bob")
    b1.spans = [Span("x", 30.0, False)]
    by_user = metrics_by_user([a1, a2, b1])
    assert by_user["alice"]["requests"] == 2
    assert by_user["bob"]["requests"] == 1
    assert by_user["bob"]["error_rate"] == 1.0
