"""lec01 — 환경 셋업 스모크 테스트.

`.env`의 DEFAULT_PROVIDER가 가리키는 프로바이더를 먼저 시도하고, 준비가 안 되어
있으면 사용 가능한 다른 프로바이더로 넘어가며 첫 LLM 호출이 도는지 확인한다.
모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec01/smoke_test.py
"""

import os

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


def available_providers(env: dict | None = None) -> list[str]:
    """환경에서 준비된 것으로 보이는 프로바이더 목록을 돌려준다.

    클라우드는 해당 API 키가 채워져 있으면, Ollama는 base URL이 있으면 후보로 본다.
    """
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    return ready


def provider_order(default: str | None, available: list[str]) -> list[str]:
    """default를 맨 앞에 두고 나머지 available을 뒤에 붙인 시도 순서를 만든다."""
    order = [default] if default and default in available else []
    order.extend(name for name in available if name not in order)
    return order


def model_and_kwargs(provider: str, env: dict | None = None) -> tuple[str, dict]:
    """프로바이더에 맞는 모델 문자열과 추가 호출 인자를 만든다."""
    env = os.environ if env is None else env
    if provider == "ollama":
        model = f"ollama/{env.get('OLLAMA_MODEL', 'gemma4:12b')}"
        return model, {"api_base": env.get("OLLAMA_API_BASE")}
    return DEFAULT_MODELS[provider], {}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    default = os.environ.get("DEFAULT_PROVIDER")
    order = provider_order(default, available_providers())

    if not order:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    # LiteLLM은 무거운 의존성이라 실제 호출 직전에 import 한다.
    import litellm

    messages = [{"role": "user", "content": "한 문장으로 자기소개를 해줘."}]
    for provider in order:
        model, kwargs = model_and_kwargs(provider)
        print(f"[{provider}] {model} 시도 중...")
        try:
            resp = litellm.completion(model=model, messages=messages, **kwargs)
        except Exception as exc:
            print(f"  실패: {type(exc).__name__} — 다음 프로바이더로 넘어갑니다")
            continue
        print(resp.choices[0].message.content)
        print(f"\n성공: {provider} / {model}")
        return 0

    print("\n모든 프로바이더 시도가 실패했습니다. 키와 Ollama 상태를 확인하세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
