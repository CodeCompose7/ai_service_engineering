"""용어 사전 도구 — 모델 바깥의 지식을 조회한다. 검색·DB 조회의 가장 단순한 형태다."""

GLOSSARY = {
    "RAG": "검색 증강 생성. 외부 문서를 검색해 LLM 답변의 근거로 삼는 방법입니다.",
    "임베딩": "텍스트를 의미를 담은 숫자 벡터로 바꾼 것입니다.",
    "function calling": "모델이 도구 호출을 요청하면 코드가 실행해 결과를 돌려주는 방식입니다.",
    "에이전트": "모델이 도구를 써서 여러 단계로 일을 처리하는 시스템입니다.",
}


def lookup_term(term: str) -> str:
    """용어 사전에서 뜻을 찾는다. 사전에 없으면 없다고 알려준다."""
    needle = term.strip().lower()
    for key, value in GLOSSARY.items():
        if key.lower() in needle or needle in key.lower():
            return value
    return "사전에 없는 용어입니다."


SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_term",
        "description": "용어 사전에서 뜻을 찾는다. 모델이 모르는 용어를 물으면 쓴다.",
        "parameters": {
            "type": "object",
            "properties": {"term": {"type": "string", "description": "찾을 용어"}},
            "required": ["term"],
        },
    },
}
