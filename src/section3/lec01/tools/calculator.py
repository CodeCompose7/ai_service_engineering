"""계산기 도구 — LLM이 자주 틀리는 정확한 산술을 맡는다."""


def calculate(a: float, b: float, op: str) -> float:
    """두 수를 사칙연산한다."""
    table = {"add": a + b, "subtract": a - b, "multiply": a * b, "divide": a / b if b else None}
    return table[op]


SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "두 수를 사칙연산한다. 정확한 산술이 필요할 때 쓴다.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "첫 번째 수"},
                "b": {"type": "number", "description": "두 번째 수"},
                "op": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "연산 종류",
                },
            },
            "required": ["a", "b", "op"],
        },
    },
}
