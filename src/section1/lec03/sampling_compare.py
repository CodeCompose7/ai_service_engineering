"""lec03 — 샘플링 파라미터(temperature·top_p·top_k) 효과 비교.

두 가지를 보여준다.

1. 파라미터 미리보기: 프로바이더마다 실제로 보낼 수 있는 인자가 다르다. OpenAI는
   top_k를 받지 않고, Anthropic은 temperature 상한이 1.0이다. 호출 없이 순수 계산으로
   각 프로바이더에 실제로 보낼 kwargs를 보여준다.
2. temperature 효과: 같은 프롬프트를 낮은/높은 temperature로 여러 번 호출해, 낮으면
   출력이 거의 같고 높으면 흔들리는 것을 눈으로 비교한다.

모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec03/sampling_compare.py
"""

import os

PROMPT = "1부터 100 사이의 정수 하나를 골라줘."

# 숫자 하나만 받으면 temperature 효과가 또렷하게 보인다. 낮으면 늘 같은 값이 나오고,
# 높이면 호출마다 값이 갈린다. 문장으로 받으면 비슷비슷해 차이가 잘 안 드러난다.
SYSTEM = "숫자 하나만 출력하세요. 다른 말은 하지 마세요."

# 프로바이더별 기본 모델 문자열. 구체 모델명은 녹화 시점 최신으로 확정한다.
DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5",
}

# 클라우드 프로바이더가 읽는 API 키 환경변수 이름.
CLOUD_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# OpenAI Chat API에는 top_k가 없어 보내면 거부된다. 나머지는 받는다.
NO_TOP_K = {"openai"}

# temperature 상한. 대부분 2.0이지만 Anthropic은 1.0까지만 받는다.
MAX_TEMPERATURE = {"anthropic": 1.0}
DEFAULT_MAX_TEMPERATURE = 2.0

# temperature 효과 비교에 쓸 값과 값마다 반복할 횟수.
TEMPERATURES = [0.0, 1.0, 1.8]
RUNS_PER_TEMPERATURE = 4


def available_providers(env: dict | None = None) -> list[str]:
    """환경에서 준비된 것으로 보이는 프로바이더 목록을 돌려준다."""
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    return ready


def provider_order(default: str | None, available: list[str]) -> list[str]:
    """default를 맨 앞에 두고 나머지 available을 뒤에 붙인 순서를 만든다."""
    order = [default] if default and default in available else []
    order.extend(name for name in available if name not in order)
    return order


def demo_provider(order: list[str]) -> str | None:
    """temperature 비교에 쓸 프로바이더를 고른다.

    클라우드 모델은 temperature 전 구간(0.0의 greedy 디코딩 포함)을 안정적으로 처리한다.
    반면 일부 로컬 모델은 temperature=0.0에서 응답이 멈추므로, 클라우드가 있으면 그쪽을
    우선한다. 클라우드가 하나도 없으면 준비된 첫 프로바이더를 그대로 쓴다.
    """
    for provider in order:
        if provider != "ollama":
            return provider
    return order[0] if order else None


def supports_top_k(provider: str) -> bool:
    """프로바이더가 top_k를 받는지 여부."""
    return provider not in NO_TOP_K


def max_temperature(provider: str) -> float:
    """프로바이더가 허용하는 temperature 상한."""
    return MAX_TEMPERATURE.get(provider, DEFAULT_MAX_TEMPERATURE)


def safe_sampling_kwargs(
    provider: str,
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> dict:
    """원하는 샘플링 값을 프로바이더가 받을 수 있는 형태로 보정한다.

    - top_k를 받지 않는 프로바이더(OpenAI)에는 top_k를 빼고,
    - temperature는 프로바이더 상한으로 잘라 범위를 넘지 않게 한다.
    - 넘기지 않은 값은 kwargs에 넣지 않아 모델 기본값을 그대로 쓴다.
    """
    kwargs: dict = {}
    if temperature is not None:
        kwargs["temperature"] = min(temperature, max_temperature(provider))
    if top_p is not None:
        kwargs["top_p"] = top_p
    if top_k is not None and supports_top_k(provider):
        kwargs["top_k"] = top_k
    return kwargs


def model_for(provider: str, env: dict | None = None) -> str:
    """프로바이더에 맞는 모델 문자열을 만든다."""
    env = os.environ if env is None else env
    if provider == "ollama":
        return f"ollama/{env.get('OLLAMA_MODEL', 'gemma4:12b')}"
    return DEFAULT_MODELS[provider]


def api_base_kwargs(provider: str, env: dict | None = None) -> dict:
    """ollama는 호스트 주소가 필요하다. 나머지는 빈 dict."""
    env = os.environ if env is None else env
    if provider == "ollama":
        return {"api_base": env.get("OLLAMA_API_BASE")}
    return {}


def preview_params(order: list[str]) -> None:
    """호출 없이, 프로바이더별로 실제 보낼 kwargs를 보여준다."""
    print("=== 파라미터 미리보기 (원하는 값: temperature=1.5, top_p=0.9, top_k=40) ===")
    for provider in order:
        kwargs = safe_sampling_kwargs(provider, temperature=1.5, top_p=0.9, top_k=40)
        note = "" if supports_top_k(provider) else "   (top_k 미지원이라 제거)"
        print(f"  {provider:10s} -> {kwargs}{note}")


def compare_temperature(provider: str) -> None:
    """같은 프롬프트를 여러 temperature로 반복 호출해 출력을 비교한다."""
    # LiteLLM은 무거운 의존성이라 실제 호출 직전에 import 한다.
    import litellm

    model = model_for(provider)
    base = api_base_kwargs(provider)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT},
    ]

    print(f"\n=== temperature 효과 비교 ({provider} / {model}) ===")
    print(f"질문: {PROMPT}  (온도만 바꿔 {RUNS_PER_TEMPERATURE}번씩)")
    for temp in TEMPERATURES:
        kwargs = safe_sampling_kwargs(provider, temperature=temp)
        used = kwargs["temperature"]
        answers = []
        for _ in range(RUNS_PER_TEMPERATURE):
            try:
                # max_tokens는 일부 Ollama 모델에서 빈 응답을 유발해 넣지 않는다.
                # 일부 모델이 멈추는 경우를 대비해 timeout을 둬 무한정 기다리지 않는다.
                resp = litellm.completion(
                    model=model, messages=messages, timeout=30, **base, **kwargs
                )
                answers.append(resp.choices[0].message.content.strip().replace("\n", " "))
            except Exception as exc:
                answers.append(f"실패({type(exc).__name__})")
        tag = f"temperature={temp}"
        if used != temp:
            tag += f"→{used}(상한)"
        print(f"  {tag:22s} {'  '.join(answers)}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    order = provider_order(os.environ.get("DEFAULT_PROVIDER"), available_providers())
    if not order:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    # 앞부분: 호출 없이 프로바이더별로 실제 보낼 인자를 보여준다.
    preview_params(order)
    # 뒷부분: temperature 효과를 실제 호출해 비교한다. temperature 0.0에서 멈추는 로컬
    # 모델이 있어, 전 구간을 안정적으로 처리하는 클라우드를 우선해 고른다.
    compare_temperature(demo_provider(order))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
