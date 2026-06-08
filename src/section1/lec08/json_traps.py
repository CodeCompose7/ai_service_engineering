"""lec08 — 구조화 출력 1: Pydantic 스키마와 프롬프트로 JSON 받기의 함정.

받고 싶은 데이터를 Pydantic 모델(Review)로 선언해 출력 계약을 만든다. 그런 다음
프롬프트만으로 JSON을 받아 보고, 두 층의 실패와 그 완화 방법을 차례로 본다.

네 가지를 보여준다.

1. 함정: 출력에 코드펜스가 붙어 파싱이 깨지고, 값이 모델을 어겨 검증이 막힌다.
2. 스키마 주입: 형식을 손으로 적는 대신 Review.model_json_schema()를 프롬프트에 넣는다.
3. JSON 모드: response_format으로 프로바이더의 JSON 모드를 켜 코드펜스를 줄인다.
4. 재시도: 검증에 실패하면 틀린 점을 알려 다시 묻고, 그게 고쳐지는지 본다.

같은 코드를 클라우드(gemini)와 로컬(ollama)로 돌려 비교한다.

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
    """받고 싶은 출력 계약. 우리가 정의한 이 모델을 출력이 따라야 한다."""

    sentiment: Literal["긍정", "부정", "중립"]
    confidence: float = Field(ge=0.0, le=1.0)  # 타입뿐 아니라 0~1 범위까지 제약
    keywords: list[str]


def schema_prompt() -> str:
    """형식을 손으로 적는 대신 Pydantic 모델에서 JSON 스키마를 뽑아 프롬프트에 넣는다."""
    schema = json.dumps(Review.model_json_schema(), ensure_ascii=False)
    return (
        "아래 JSON 스키마를 그대로 따르는 JSON으로만 답해라. 코드펜스·설명 없이.\n"
        f"스키마: {schema}\n"
        f"리뷰: {REVIEW_TEXT}"
    )


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
    """우리가 정의한 Review 모델로 검증한다. (성공 여부, 첫 오류 요약)."""
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


def ask(model: str, prompt: str = PROMPT, json_mode: bool = False, **kwargs) -> str:
    """한 번 호출하고 본문을 돌려준다. json_mode면 프로바이더의 JSON 모드를 켠다."""
    import litellm

    extra = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=120,
        **extra,
        **kwargs,
    )
    return resp.choices[0].message.content


def request_with_retry(
    model: str, kwargs: dict, max_retries: int = 2
) -> tuple[Review | None, list[str]]:
    """검증에 실패하면 틀린 점을 모델에 알려 재시도한다. (Review 또는 None, 시도 로그)."""
    import litellm

    messages = [{"role": "user", "content": PROMPT}]
    log: list[str] = []
    for attempt in range(1, max_retries + 2):
        resp = litellm.completion(model=model, messages=messages, timeout=120, **kwargs)
        text = resp.choices[0].message.content
        data = parse_with_guard(text)
        if data is not None:
            ok, err = validate(data)
            if ok:
                log.append(f"{attempt}회차: 성공")
                return Review(**data), log
            log.append(f"{attempt}회차: 검증 실패 — {err}")
            feedback = f"방금 답은 틀렸다: {err}. 스키마를 지켜 JSON만 다시 답해라."
        else:
            log.append(f"{attempt}회차: 파싱 실패")
            feedback = "JSON만, 코드펜스 없이 다시 답해라."
        # 모델에게 직전 답과 무엇이 틀렸는지 알려 재호출한다.
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": feedback})
    return None, log


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def demo_traps(backends: list[tuple[str, str, dict]]) -> None:
    """프롬프트만으로 JSON을 받아 원시 파싱 → 가드 → 검증의 세 단계를 거친다."""
    print("=== 1. 프롬프트만으로 JSON 받기 — 두 층의 함정 ===")
    print(f"리뷰: {REVIEW_TEXT}")
    for label, model, kwargs in backends:
        try:
            text = ask(model, **kwargs)
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
        print(f"  가드 후 파싱: 성공 / Pydantic 검증: {'성공' if ok else f'실패 — {err}'}")


def demo_json_mode(backends: list[tuple[str, str, dict]]) -> None:
    """JSON 모드를 켜면 코드펜스가 사라지는지 본다. 일반 호출과 원시 출력을 비교한다."""
    print("\n\n=== 2. JSON 모드(response_format)로 코드펜스 줄이기 ===")
    for label, model, kwargs in backends:
        try:
            normal = ask(model, **kwargs)
            jsonm = ask(model, json_mode=True, **kwargs)
        except Exception as exc:
            print(f"\n[{label}] {model}\n  JSON 모드 미지원/실패: {type(exc).__name__}")
            continue
        normal_ok = "성공" if raw_parses(normal) else "실패"
        jsonm_ok = "성공" if raw_parses(jsonm) else "실패"
        print(f"\n[{label}] {model}")
        print(f"  일반:     raw json.loads {normal_ok} :: {_oneline(normal)[:55]}")
        print(f"  JSON 모드: raw json.loads {jsonm_ok} :: {_oneline(jsonm)[:55]}")


def demo_retry(backends: list[tuple[str, str, dict]]) -> None:
    """검증 실패를 재시도로 고친다. 틀린 점을 알려 다시 묻는다."""
    print("\n\n=== 3. 검증 실패를 재시도로 고치기 ===")
    for label, model, kwargs in backends:
        try:
            review, log = request_with_retry(model, kwargs, max_retries=2)
        except Exception as exc:
            print(f"\n[{label}] {model}\n  실패: {type(exc).__name__}")
            continue
        print(f"\n[{label}] {model}")
        for line in log:
            print(f"  {line}")
        print(f"  → {review!r}" if review else "  → 최종 실패")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    backends = targets()
    if not backends:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    demo_traps(backends)
    print("\n\n=== 스키마를 프롬프트에 넣기 (model_json_schema) ===")
    print(_oneline(schema_prompt())[:200])
    demo_json_mode(backends)
    demo_retry(backends)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
