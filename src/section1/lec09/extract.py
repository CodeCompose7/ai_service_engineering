"""lec09 — 구조화 출력 2: instructor로 검증·재시도를 자동화.

lec08에서 손으로 짠 파싱·정리·검증·재시도를 instructor가 대신한다. Pydantic 모델을
response_model로 넘기면, 검증을 통과한 객체를 바로 돌려받는다. instructor도 LiteLLM
위에서 돌므로, 모델 문자열만 바꾸면 클라우드(gemini)와 로컬(ollama)을 같은 코드로 오간다.

extract_review가 이 단위의 산출물이다. 문자열을 검증된 Review로 뽑아내는 안전한 함수다.
extract_reviews는 response_model=list[Review]로 한 호출에서 여러 객체를 받는다.

백엔드를 바꿀 때는 instructor의 모드만 손본다. 기본 모드는 tool calling이라 OpenAI·gemini엔
잘 맞지만, ollama 같은 백엔드는 모델마다 tool calling 지원이 달라 JSON 모드가 안전하다
(lec07). 작은 로컬 모델은 lec08의 정규화 모델을 곁들이면 더 안정적이다.

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
MULTI_TEXT = (
    "배송이 정말 빨라서 좋았어요. 다만 고객센터 응대는 불친절했습니다. "
    "가격은 그냥 무난한 편이에요."
)


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


class StrictKeywordReview(Review):
    """검증 규칙을 더한 예. keywords를 한 단어로 제한한다.

    규칙을 어기면(예: '포장 허술') ValueError를 던지고, instructor가 그 오류 메시지를
    모델에 돌려주며 재시도한다. 타입뿐 아니라 우리가 정한 규칙으로 재시도를 부를 수 있다.
    """

    @field_validator("keywords")
    @classmethod
    def _single_word(cls, value):
        for keyword in value:
            if " " in keyword.strip():
                raise ValueError(f"키워드는 한 단어여야 합니다: '{keyword}'")
        return value


class ReviewReport(BaseModel):
    """글 전체를 한 번에 정리하는 중첩 모델. 총평·측면별 분석·요약을 함께 담는다.

    aspects가 list[Review]로 중첩돼, instructor가 한 호출로 바깥 객체와 안쪽 목록을
    모두 채워 검증한다.
    """

    overall: Literal["긍정", "부정", "중립"] = Field(description="글 전체의 총평")
    aspects: list[Review] = Field(description="측면별 분석 목록")
    summary: str = Field(description="글 전체를 한 줄로 요약")


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


def extract_reviews(
    text: str,
    model: str = CLOUD_MODEL,
    json_mode: bool = False,
    max_retries: int = 2,
    **kwargs,
) -> list[Review]:
    """글에서 여러 Review를 목록으로 뽑는다. response_model=list[Review].

    instructor에 list[Model]을 주면 한 호출로 여러 객체를 받는다. 한 글에 여러 측면이
    섞여 있을 때 측면별로 검증된 객체 목록을 돌려준다.
    """
    client = make_client(json_mode=json_mode)
    prompt = f"다음 글에 담긴 리뷰들을 측면별로 각각 분석해 목록으로 만들어줘.\n{text}"
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=list[Review],
        max_retries=max_retries,
        **kwargs,
    )


def extract_report(
    text: str,
    model: str = CLOUD_MODEL,
    json_mode: bool = False,
    max_retries: int = 2,
    **kwargs,
) -> ReviewReport:
    """글을 ReviewReport(총평+측면별+요약)로 한 번에 뽑는다. 중첩 모델도 한 호출로 받는다."""
    client = make_client(json_mode=json_mode)
    prompt = f"다음 글을 분석해 총평·측면별 분석·한 줄 요약으로 정리해줘.\n{text}"
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=ReviewReport,
        max_retries=max_retries,
        **kwargs,
    )


def extract_review_safe(text: str, models: list[str], **kwargs) -> Review:
    """모델 목록을 차례로 시도하고, 검증까지 실패하면 다음 모델로 폴백한다.

    lec06의 폴백을 구조화 출력으로 옮긴 것이다. ollama 백엔드는 JSON 모드·정규화 모델로
    맞춘다. 모두 실패하면 마지막 예외를 올려, 호출부가 기본값 등으로 대응하게 한다.
    """
    last_exc: Exception | None = None
    for model in models:
        json_mode = model.startswith("ollama/")
        response_model = NormalizedReview if json_mode else Review
        try:
            return extract_review(
                text, model=model, response_model=response_model, json_mode=json_mode, **kwargs
            )
        except Exception as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise ValueError("models가 비어 있습니다")


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
    """(라벨, 모델, 추가 kwargs) 목록. 준비된 클라우드·ollama만 담는다.

    ollama는 모델 이름이 -cloud면 Ollama Cloud, 아니면 로컬로 라벨한다. OLLAMA_API_KEY가
    있으면 함께 넘긴다. 로컬 모델은 키가 없어도 되고, 클라우드 모델은 로그인된 데몬을
    거치거나 이 키로 인증한다.
    """
    env = os.environ if env is None else env
    out: list[tuple[str, str, dict]] = []
    if have_cloud(env):
        out.append(("클라우드", CLOUD_MODEL, {}))
    if have_local(env):
        model = local_model(env)
        label = "Ollama Cloud" if model.endswith("-cloud") else "로컬"
        opts = {"api_base": env.get("OLLAMA_API_BASE")}
        if env.get("OLLAMA_API_KEY"):
            opts["api_key"] = env["OLLAMA_API_KEY"]
        out.append((label, model, opts))
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


def _backend_opts(model: str) -> tuple[bool, type]:
    """모델에 맞는 (json_mode, response_model)을 고른다. ollama(로컬·클라우드)는
    tool calling이 흔들려 JSON 모드가 안전하고, 정규화 모델로 사소한 흔들림을 흡수한다.
    gemini는 기본 모드로 충분하다."""
    if model.startswith("ollama/"):
        return True, NormalizedReview
    return False, Review


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    backends = targets()
    if not backends:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    print("=== 1. 검증된 Review 한 개 뽑기 ===")
    print(f"리뷰: {REVIEW_TEXT}")
    for label, model, kwargs in backends:
        json_mode, rm = _backend_opts(model)
        try:
            review, retries = extract_counting_retries(
                REVIEW_TEXT, model, response_model=rm, json_mode=json_mode, **kwargs
            )
        except Exception as exc:
            print(f"\n[{label}] {model}\n  실패: {type(exc).__name__}")
            continue
        print(f"\n[{label}] {model}  (재시도 {retries}회)")
        print(f"  → {review!r}")

    # 여러 객체(list)는 tool calling 모드가 흔들리므로 모든 백엔드에서 JSON 모드를 쓴다.
    print("\n\n=== 2. 여러 개를 한 번에 — list[Review] (JSON 모드) ===")
    print(f"글: {MULTI_TEXT}")
    for label, model, kwargs in backends:
        try:
            reviews = extract_reviews(MULTI_TEXT, model=model, json_mode=True, **kwargs)
        except Exception as exc:
            print(f"\n[{label}] {model}\n  실패: {type(exc).__name__}")
            continue
        print(f"\n[{label}] {model} — {len(reviews)}개")
        for review in reviews:
            print(f"  → {review!r}")

    # 중첩 모델도 복잡한 스키마라 JSON 모드로 받는다.
    print("\n\n=== 3. 중첩 모델 — ReviewReport ===")
    print(f"글: {MULTI_TEXT}")
    for label, model, kwargs in backends:
        try:
            report = extract_report(MULTI_TEXT, model=model, json_mode=True, **kwargs)
        except Exception as exc:
            print(f"\n[{label}] {model}\n  실패: {type(exc).__name__}")
            continue
        print(f"\n[{label}] {model} — 총평 {report.overall}, 측면 {len(report.aspects)}개")
        print(f"  요약: {report.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
