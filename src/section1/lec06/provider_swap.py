"""lec06 — LiteLLM 멀티 프로바이더.

모델 문자열만 바꿔 여러 프로바이더를 오간다. 호출하는 함수도, 메시지 구조도, 응답을
꺼내는 방식도 그대로다. 준비된 프로바이더(gemini·openai·anthropic·ollama)에 같은
메시지를 보내 본문·토큰·비용을 나란히 비교한다.

핵심 산출물은 chat 래퍼다. 프로바이더 차이를 한 함수에 모아, 호출부는 chat(messages)만
알면 된다. 모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec06/provider_swap.py
"""

import os

# 프로바이더별 기본 모델 문자열. 구체 모델명은 녹화 시점 최신으로 확정한다.
DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5",
}
CLOUD_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# chat 래퍼의 기본 모델.
DEFAULT_MODEL = DEFAULT_MODELS["gemini"]

PROMPT = "LiteLLM을 한 문장으로 설명해줘."


def available_providers(env: dict | None = None) -> list[str]:
    """환경에서 준비된 것으로 보이는 프로바이더 목록을 돌려준다."""
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    return ready


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


def provider_models(providers: list[str], env: dict | None = None) -> list[tuple[str, str]]:
    """(프로바이더, 모델 문자열) 목록을 만든다. 데모가 이 순서대로 돈다."""
    return [(provider, model_for(provider, env)) for provider in providers]


def chat(messages: list[dict], model: str = DEFAULT_MODEL, **kwargs) -> str:
    """프로바이더 무관하게 호출하고 본문 텍스트만 돌려준다. 이 단위의 산출물.

    호출부는 chat(messages)만 알면 되고, 기본 모델을 바꾸거나 프로바이더별 예외를
    처리할 일이 생기면 이 함수 안에서만 손본다.
    """
    import litellm

    resp = litellm.completion(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content


def _complete(model: str, messages: list[dict], **kwargs):
    import litellm

    return litellm.completion(model=model, messages=messages, timeout=60, **kwargs)


def _cost(resp) -> float | None:
    """LiteLLM이 응답에서 계산해 주는 호출 비용(USD). 모르는 모델이면 None."""
    import litellm

    try:
        cost = litellm.completion_cost(completion_response=resp)
        return cost if cost else None
    except Exception:
        return None


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    providers = available_providers()
    if not providers:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    messages = [{"role": "user", "content": PROMPT}]
    print("=== 모델 문자열만 바꿔 여러 프로바이더로 ===")
    print(f"질문: {PROMPT}")
    for provider, model in provider_models(providers):
        kwargs = api_base_kwargs(provider)
        try:
            resp = _complete(model, messages, **kwargs)
        except Exception as exc:
            print(f"\n[{provider}] {model}")
            print(f"  실패: {type(exc).__name__} — 키나 연결을 확인하세요")
            continue
        usage = resp.usage
        cost = _cost(resp)
        cost_str = f"${cost:.6f}" if cost is not None else "-(로컬·무료)"
        print(f"\n[{provider}] {model}")
        print(f"  본문: {_oneline(resp.choices[0].message.content)}")
        print(f"  토큰: prompt={usage.prompt_tokens} completion={usage.completion_tokens}")
        print(f"  비용: {cost_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
