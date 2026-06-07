"""lec06 — LiteLLM 멀티 프로바이더.

모델 문자열만 바꿔 여러 프로바이더를 오간다. 호출하는 함수도, 메시지 구조도, 응답을
꺼내는 방식도 그대로다. 세 가지를 보여준다.

1. 프로바이더 교체 비교: 같은 메시지를 네 곳에 보내 본문·토큰·비용을 나란히 본다.
2. 래퍼가 차이를 흡수: OpenAI가 받지 않는 top_k를 chat 래퍼가 알아서 빼고 부른다.
3. 폴백: primary 모델이 실패하면 LiteLLM이 다음 모델로 자동으로 넘어간다.

핵심 산출물은 chat 래퍼다. 프로바이더 차이를 한 함수에 모아, 호출부는 chat(messages)만
알면 된다. 모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec06/provider_swap.py
"""

import logging
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

# 프로바이더가 받지 않는 파라미터. 래퍼가 알아서 빼 준다. lec03에서 본 OpenAI의 top_k가 예다.
PROVIDER_UNSUPPORTED = {"openai": {"top_k"}}

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


def provider_of(model: str) -> str:
    """모델 문자열의 접두사로 프로바이더 이름을 뽑는다. openai/gpt-4o-mini -> openai."""
    return model.split("/", 1)[0]


def safe_kwargs(model: str, kwargs: dict) -> dict:
    """모델이 받지 않는 파라미터를 빼 준다. 지금은 OpenAI의 top_k."""
    drop = PROVIDER_UNSUPPORTED.get(provider_of(model), set())
    return {key: value for key, value in kwargs.items() if key not in drop}


def chat(messages: list[dict], model: str = DEFAULT_MODEL, **kwargs) -> str:
    """프로바이더 무관하게 호출하고 본문 텍스트만 돌려준다. 이 단위의 산출물.

    모델이 못 받는 파라미터는 알아서 빼고 부른다. 호출부는 chat(messages)만 알면 되고,
    기본 모델을 바꾸거나 프로바이더별 예외를 처리할 일이 생기면 이 함수 안에서만 손본다.
    """
    import litellm

    resp = litellm.completion(model=model, messages=messages, **safe_kwargs(model, kwargs))
    return resp.choices[0].message.content


def chat_with_fallback(
    messages: list[dict], model: str, fallbacks: list[str], **kwargs
) -> tuple[str, str]:
    """primary가 실패하면 fallbacks의 모델로 자동으로 넘어간다. (응답 모델, 본문)을 돌려준다."""
    import litellm

    resp = litellm.completion(
        model=model, messages=messages, fallbacks=fallbacks, **safe_kwargs(model, kwargs)
    )
    return resp.model, resp.choices[0].message.content


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


def _quiet_litellm() -> None:
    """폴백 데모에서 primary 실패 로그가 시끄러우니 LiteLLM 로거를 조용히 둔다."""
    import litellm

    litellm.suppress_debug_info = True
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def demo_swap(providers: list[str]) -> None:
    """같은 메시지를 프로바이더마다 보내 본문·토큰·비용을 비교한다."""
    print("=== 1. 모델 문자열만 바꿔 여러 프로바이더로 ===")
    print(f"질문: {PROMPT}")
    messages = [{"role": "user", "content": PROMPT}]
    for provider, model in provider_models(providers):
        try:
            resp = _complete(model, messages, **api_base_kwargs(provider))
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


def demo_wrapper(providers: list[str]) -> None:
    """래퍼가 프로바이더 차이를 흡수하는 것을 보인다. OpenAI에 top_k를 줘도 알아서 뺀다."""
    print("\n\n=== 2. 래퍼가 차이를 흡수 — OpenAI에 top_k ===")
    if "openai" not in providers:
        print("  (openai 키가 없어 건너뜀)")
        return
    messages = [{"role": "user", "content": "바다 색을 한 단어로."}]
    # top_k는 OpenAI가 거부하지만, chat 래퍼가 알아서 빼 줘서 호출이 성공한다.
    answer = chat(messages, model="openai/gpt-4o-mini", top_k=5, temperature=0.0)
    print(f"  chat(..., top_k=5) -> {_oneline(answer)}")
    print("  (top_k는 래퍼가 제거하고 호출했다)")


def demo_fallback(providers: list[str]) -> None:
    """primary 모델이 실패하면 폴백 모델로 자동으로 넘어가는 것을 보인다."""
    print("\n\n=== 3. 폴백 — primary가 실패하면 다음 모델로 ===")
    if "gemini" not in providers:
        print("  (폴백 데모에 gemini가 필요해 건너뜀)")
        return
    _quiet_litellm()
    messages = [{"role": "user", "content": "바다 색을 한 단어로."}]
    primary = "anthropic/claude-does-not-exist"  # 일부러 없는 모델
    answered_model, answer = chat_with_fallback(messages, primary, ["gemini/gemini-2.5-flash"])
    print(f"  primary: {primary}  (실패)")
    print(f"  실제 응답 모델: {answered_model}")
    print(f"  본문: {_oneline(answer)}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    providers = available_providers()
    if not providers:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    demo_swap(providers)
    demo_wrapper(providers)
    demo_fallback(providers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
