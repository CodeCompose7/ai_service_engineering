"""lec02 비동기 LLM 호출 — lec01 llm(동기)의 async 짝.

lec01 llm은 completion·complete로 동기 호출만 한다. lec01 강의는 async를 쓰지 않으므로 그대로
두고, lec02의 비동기 도구·에이전트가 await로 부를 수 있는 async 버전을 여기 따로 둔다. 프로바이더
선택은 lec01의 resolve_model을 공유한다.

asyncio는 단일 스레드로 돌아 호출 카운트 증가가 await 사이에서 끊기지 않으므로 별도 락이 필요 없다.
"""

from section3.lec01.llm import resolve_model

_call_count = 0


async def acompletion(model: str, messages: list[dict], **kwargs):
    """completion의 async 짝. await로 LiteLLM을 부르고 횟수를 센다."""
    global _call_count
    import litellm

    _call_count += 1
    return await litellm.acompletion(model=model, messages=messages, **kwargs)


async def acomplete(messages: list[dict]) -> str:
    """complete의 async 짝. 도구 없이 비동기로 한 번 생성한다."""
    model, kwargs = resolve_model()
    resp = await acompletion(model, messages, **kwargs)
    return resp.choices[0].message.content


def reset_calls() -> None:
    """호출 횟수를 0으로 되돌린다."""
    global _call_count
    _call_count = 0


def call_count() -> int:
    """마지막 reset 이후의 비동기 LiteLLM 호출 횟수."""
    return _call_count
