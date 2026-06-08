"""lec08 — 구조화 출력 1: 프롬프트만으로 JSON 받기의 함정.

받고 싶은 데이터를 Pydantic 모델(Review)로 선언해 출력 계약을 만든다. 그런 다음
프롬프트만으로 JSON을 받아 보고, 두 층의 실패를 드러낸다.

1. 파싱 실패: 출력에 코드펜스나 설명이 붙거나 잘려서 json.loads가 깨진다.
2. 검증 실패: 파싱은 되지만 값이 계약을 어겨 Pydantic이 막는다.

임시 가드(extract_json)로 파싱 실패의 일부는 막을 수 있지만, 매번 손으로 짜기엔
지저분하다는 것을 보인다. 같은 코드를 클라우드(gemini)와 로컬(ollama)로 돌려 비교한다.

실행:
    uv run python src/section1/lec08/json_traps.py
"""

import json
import os
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

CLOUD_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_LOCAL_MODEL = "gemma4:12b"

REVIEW_TEXT = "배송은 빨랐는데 포장이 너무 허술했어요."
PROMPT = (
    "다음 리뷰를 분석해 JSON으로만 답해라.\n"
    '형식: {"sentiment": "긍정|부정|중립", "confidence": 0~1 실수, "keywords": [문자열]}\n'
    f"리뷰: {REVIEW_TEXT}"
)


class Review(BaseModel):
    """받고 싶은 출력 계약. 어떤 필드가 어떤 타입이어야 하는지를 선언한다."""

    sentiment: Literal["긍정", "부정", "중립"]
    confidence: float = Field(ge=0.0, le=1.0)  # 타입뿐 아니라 0~1 범위까지 제약
    keywords: list[str]


def extract_json(text: str) -> str:
    """모델 출력에서 JSON만 추려 본다. 코드펜스를 벗기고 첫 '{'부터 마지막 '}'까지 잘라낸다.

    완벽하지 않은 임시 가드다. 코드펜스와 앞뒤 군더더기 정도만 막는다.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


def raw_parses(text: str) -> bool:
    """원시 문자열이 그대로 json.loads로 파싱되는가."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def parse_with_guard(text: str) -> dict | None:
    """가드로 정리한 뒤 파싱한다. 실패면 None."""
    try:
        result = json.loads(extract_json(text))
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def validate(data: dict) -> tuple[bool, str]:
    """Pydantic으로 계약을 검증한다. (성공 여부, 첫 오류 요약)."""
    try:
        Review(**data)
        return True, ""
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(part) for part in first["loc"])
        return False, f"{loc}: {first['msg']}"


def have_cloud(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("GEMINI_API_KEY"))


def have_local(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("OLLAMA_API_BASE"))


def local_model(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    return f"ollama/{env.get('OLLAMA_MODEL', DEFAULT_LOCAL_MODEL)}"


def targets(env: dict | None = None) -> list[tuple[str, str, dict]]:
    """(라벨, 모델, 추가 kwargs) 목록. 준비된 클라우드·로컬만 담는다."""
    env = os.environ if env is None else env
    out: list[tuple[str, str, dict]] = []
    if have_cloud(env):
        out.append(("클라우드", CLOUD_MODEL, {}))
    if have_local(env):
        out.append(("로컬", local_model(env), {"api_base": env.get("OLLAMA_API_BASE")}))
    return out


def _ask(model: str, **kwargs) -> str:
    import litellm

    resp = litellm.completion(
        model=model, messages=[{"role": "user", "content": PROMPT}], timeout=120, **kwargs
    )
    return resp.choices[0].message.content


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    backends = targets()
    if not backends:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    print("=== 프롬프트만으로 JSON 받기 ===")
    print(f"리뷰: {REVIEW_TEXT}")
    for label, model, kwargs in backends:
        try:
            text = _ask(model, **kwargs)
        except Exception as exc:
            print(f"\n[{label}] {model}\n  호출 실패: {type(exc).__name__}")
            continue
        print(f"\n[{label}] {model}")
        print(f"  원시 출력: {_oneline(text)[:110]}")
        print(f"  raw json.loads: {'성공' if raw_parses(text) else '실패'}")
        data = parse_with_guard(text)
        if data is None:
            print("  가드 후 파싱: 실패")
            continue
        ok, err = validate(data)
        verdict = "성공" if ok else f"실패 — {err}"
        print(f"  가드 후 파싱: 성공 / Pydantic 검증: {verdict}")
        if ok:
            print(f"  → {Review(**data)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
