"""lec01 — LLM 호출 공통.

프로바이더를 고르고 LiteLLM로 부르는 부분을 모아 둔다. fc.py의 도구 호출 loop와
search_wikipedia 도구의 요약이 같은 방식으로 모델을 쓰도록, 그리고 순환 import를 피하도록
도구·loop가 함께 의존하는 이 한 곳에 둔다.
"""

import os

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


def resolve_model(env: dict | None = None) -> tuple[str, dict]:
    """`.env`의 DEFAULT_PROVIDER가 가리키는 프로바이더를 앞세운다. 없으면 준비된 것으로 폴백한다."""
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    default = env.get("DEFAULT_PROVIDER")
    order = ([default] if default in ready else []) + [n for n in ready if n != default]
    if not order:
        raise RuntimeError("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄우세요.")
    provider = order[0]
    if provider == "ollama":
        model = f"ollama/{env.get('OLLAMA_MODEL', 'gemma4:12b')}"
        return model, {"api_base": env.get("OLLAMA_API_BASE")}
    return DEFAULT_MODELS[provider], {}


_call_count = 0


def completion(model: str, messages: list[dict], **kwargs):
    """모든 LiteLLM 호출을 이 한 곳으로 모아 횟수를 센다. 도구 호출이든 요약이든 다 거친다."""
    global _call_count
    import litellm

    _call_count += 1
    return litellm.completion(model=model, messages=messages, **kwargs)


def reset_calls() -> None:
    """호출 횟수를 0으로 되돌린다."""
    global _call_count
    _call_count = 0


def call_count() -> int:
    """마지막 reset 이후의 LiteLLM 호출 횟수."""
    return _call_count


def complete(messages: list[dict]) -> str:
    """도구 없이 한 번 생성한다. 요약처럼 단순한 호출에 쓴다."""
    model, kwargs = resolve_model()
    resp = completion(model, messages, **kwargs)
    return resp.choices[0].message.content


async def acompletion(model: str, messages: list[dict], **kwargs):
    """completion의 async 짝. lec02 비동기 도구·에이전트가 await로 부른다."""
    global _call_count
    import litellm

    _call_count += 1
    return await litellm.acompletion(model=model, messages=messages, **kwargs)


async def acomplete(messages: list[dict]) -> str:
    """complete의 async 짝. 도구 없이 비동기로 한 번 생성한다."""
    model, kwargs = resolve_model()
    resp = await acompletion(model, messages, **kwargs)
    return resp.choices[0].message.content
