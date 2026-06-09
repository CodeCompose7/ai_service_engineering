"""lec01 도구 모음.

도구 하나를 한 파일에 두고, 여기서 모아 등록한다. 각 도구 모듈은 실행 함수와 SCHEMA(모델에
주는 도구 설명)를 내보낸다. TOOLS는 모델에 넘길 스키마 목록이고, run_tool은 이름으로 알맞은
함수를 찾아 실제로 실행한다. 도구를 늘리려면 파일을 더하고 _REGISTRY에 한 줄을 넣는다.
"""

from .calculator import SCHEMA as _CALC
from .calculator import calculate
from .clock import SCHEMA as _CLOCK
from .clock import current_time
from .glossary import SCHEMA as _GLOSSARY
from .glossary import lookup_term
from .search_wikipedia import SCHEMA as _WIKI
from .search_wikipedia import search_wikipedia

# 도구 이름 → (실행 함수, 스키마)
_REGISTRY = {
    "calculate": (calculate, _CALC),
    "current_time": (current_time, _CLOCK),
    "lookup_term": (lookup_term, _GLOSSARY),
    "search_wikipedia": (search_wikipedia, _WIKI),
}

# 모델에 넘길 스키마 목록
TOOLS = [schema for _, schema in _REGISTRY.values()]


def run_tool(name: str, args: dict):
    """모델이 요청한 도구를 실제로 실행한다. 실행은 모델이 아니라 우리 코드가 한다."""
    if name not in _REGISTRY:
        raise ValueError(f"모르는 도구: {name}")
    func, _ = _REGISTRY[name]
    return func(**args)
