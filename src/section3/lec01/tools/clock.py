"""시계 도구 — 모델이 알 수 없는 실시간 값(지금 시각)을 알려준다."""

from datetime import datetime


def current_time() -> str:
    """지금 날짜와 시각을 돌려준다. 모델은 현재 시각을 알지 못한다."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = {
    "type": "function",
    "function": {
        "name": "current_time",
        "description": "지금 날짜와 시각을 알려준다. 현재 시각이 필요할 때 쓴다.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
