"""clock 도구 테스트."""

import re

from section3.lec01.tools.clock import current_time


def test_current_time_format():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", current_time())
