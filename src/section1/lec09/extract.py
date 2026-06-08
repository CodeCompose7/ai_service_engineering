"""lec09 — 구조화 출력 2: instructor로 검증·재시도를 자동화.

lec08에서 손으로 짠 파싱·정리·검증·재시도를 instructor가 대신한다. Pydantic 모델을
response_model로 넘기면, 검증을 통과한 객체를 바로 돌려받는다. instructor도 LiteLLM
위에서 돌므로, 모델 문자열만 바꾸면 클라우드(gemini)와 로컬(ollama)을 같은 코드로 오간다.

로컬을 안정적으로 돌리려면 S1에서 본 두 가지가 함께 필요하다.
- JSON 모드: instructor 기본 모드는 tool calling인데, lec07에서 봤듯 로컬은 tool calling이
  약하다. JSON 모드로 붙이면 그 약점을 피한다.
- 정규화 validator: lec08의 field_validator로 ' 중립' 같은 공백 흔들림을 검증 전에 흡수한다.

extract_review가 이 단위의 산출물이다. 문자열을 검증된 Review로 뽑아내는 안전한 함수다.

실행:
    uv run python src/section1/lec09/extract.py
"""

import os
from typing import Literal

import instructor
import litellm
from pydantic import BaseModel, Field, field_validator

CLOUD_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_LOCAL_MODEL = "gemma4:12b"
REVIEW_TEXT = "배송은 빨랐는데 포장이 너무 허술했어요."


class Review(BaseModel):
    """lec08과 같은 출력 모델. instructor가 이 모델로 파싱·검증한다."""

    sentiment: Literal["긍정", "부정", "중립"] = Field(description="리뷰의 전반적 감정")
    confidence: float = Field(ge=0.0, le=1.0, description="판단 확신도, 0~1 실수")
    keywords: list[str] = Field(description="리뷰의 핵심 키워드")


class NormalizedReview(Review):
    """lec08의 정규화 validator를 더한 변형. sentiment의 앞뒤 공백을 검증 전에 떼어,
    로컬 모델이 자주 내는 ' 중립' 같은 값을 재시도 없이 흡수한다."""

    @field_validator("sentiment", mode="before")
    @classmethod
    def _strip_sentiment(cls, value):
        return value.strip() if isinstance(value, str) else value


def make_client(json_mode: bool = False):
    """instructor를 LiteLLM에 붙인다. json_mode면 tool calling 대신 JSON 모드를 쓴다.

    기본 모드는 tool calling(Mode.TOOLS)이라 그것을 지원하는 클라우드 모델엔 잘 맞지만,
    tool calling이 약한 로컬 모델에는 Mode.JSON이 안정적이다.
    """
    mode = instructor.Mode.JSON if json_mode else instructor.Mode.TOOLS
    return instructor.from_litellm(litellm.completion, mode=mode)


_DEFAULT_CLIENT = make_client(json_mode=False)


def extract_review(
    text: str,
    model: str = CLOUD_MODEL,
    response_model: type = Review,
    json_mode: bool = False,
    max_retries: int = 2,
    **kwargs,
) -> Review:
    """문자열을 검증된 Review 객체로 뽑아낸다. 이 단위의 산출물.

    instructor가 파싱·검증·재시도를 안에서 처리하므로, 호출부는 검증된 객체만 받는다.
    모델 문자열만 바꾸면 프로바이더가 바뀐다. 로컬에는 json_mode=True와
    response_model=NormalizedReview가 안정적이다.
    """
    client = make_client(json_mode=True) if json_mode else _DEFAULT_CLIENT
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": f"다음 리뷰를 분석해줘.\n{text}"}],
        response_model=response_model,
        max_retries=max_retries,
        **kwargs,
    )


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


def extract_counting_retries(
    text: str, model: str, response_model: type = Review, json_mode: bool = False, **kwargs
) -> tuple[Review, int]:
    """추출하면서 재시도(파싱·검증 실패) 횟수를 센다. 데모용으로 새 client에 훅을 단다."""
    client = make_client(json_mode=json_mode)
    retries = {"n": 0}
    client.on("parse:error", lambda *args, **kw: retries.__setitem__("n", retries["n"] + 1))
    review = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": f"다음 리뷰를 분석해줘.\n{text}"}],
        response_model=response_model,
        max_retries=2,
        **kwargs,
    )
    return review, retries["n"]


def _run(backends, response_model, json_mode) -> None:
    for label, model, kwargs in backends:
        try:
            review, retries = extract_counting_retries(
                REVIEW_TEXT, model, response_model=response_model, json_mode=json_mode, **kwargs
            )
        except Exception as exc:
            print(f"\n[{label}] {model}")
            print(f"  최종 실패: {type(exc).__name__} (max_retries 소진)")
            continue
        print(f"\n[{label}] {model}  (재시도 {retries}회)")
        print(f"  → {review!r}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    backends = targets()
    if not backends:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    print("=== 1. 기본 모드(tool calling) + Review ===")
    print(f"리뷰: {REVIEW_TEXT}")
    _run(backends, response_model=Review, json_mode=False)

    print("\n\n=== 2. JSON 모드 + 정규화 validator (로컬에 안정적) ===")
    _run(backends, response_model=NormalizedReview, json_mode=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
