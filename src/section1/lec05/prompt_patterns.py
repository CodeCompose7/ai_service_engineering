"""lec05 — 프롬프트 패턴.

같은 모델이라도 무엇을 어떻게 시키느냐에 따라 출력이 달라진다. 빈약한 프롬프트와
설계된 프롬프트를 클라우드(gemini)와 로컬(ollama) 두 백엔드로 나란히 돌려 차이를 본다.

두 가지를 보여준다.

1. 빈약한 vs 설계된 프롬프트: 허용 목록과 출력 형식을 박으면 출력이 한 단어로 깔끔해진다.
2. few-shot: 경계 사례에 예시 몇 개를 보여주면 형식과 판단이 안정된다.

모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec05/prompt_patterns.py
"""

import os

DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
}
CLOUD_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
}
TARGET_ORDER = ["gemini", "ollama"]

# 문의 분류에 쓸 카테고리.
CATEGORIES = ["결제", "배송", "환불"]

# 감정 분류 few-shot 예시. (입력, 정답 라벨)
SENTIMENT_EXAMPLES = [
    ("배송이 정말 빨라서 좋았어요.", "긍정"),
    ("포장이 다 찢어져서 왔네요.", "부정"),
]


def available_providers(env: dict | None = None) -> list[str]:
    """환경에서 준비된 것으로 보이는 프로바이더 목록을 돌려준다."""
    env = os.environ if env is None else env
    ready = [name for name, key in CLOUD_KEY_ENV.items() if env.get(key)]
    if env.get("OLLAMA_API_BASE"):
        ready.append("ollama")
    return ready


def target_providers(available: list[str]) -> list[str]:
    """비교에 쓸 프로바이더를 정해진 순서(gemini, ollama)로 추린다."""
    return [p for p in TARGET_ORDER if p in available]


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


def bare_classify(text: str) -> list[dict]:
    """빈약한 프롬프트: 그냥 분류해 달라고만 한다. 형식 제약이 없다."""
    return [{"role": "user", "content": f"이 고객 문의를 분류해줘: {text}"}]


def designed_classify(text: str) -> list[dict]:
    """설계된 프롬프트: 허용 목록과 출력 형식을 system에 박는다."""
    system = (
        f"너는 고객 문의 분류기다. 카테고리는 {', '.join(CATEGORIES)} 중 하나다. "
        "다른 말 없이 그 카테고리 단어 하나만 출력한다."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]


def sentiment_messages(text: str, with_examples: bool) -> list[dict]:
    """감정 분류 메시지를 만든다.

    형식을 말로 강제하지 않고 약하게만 지시한다. few-shot 예시가 라벨과 한 단어 형식을
    대신 가르치는지 보려는 것이다. with_examples면 예시를 user/assistant로 끼워 넣는다.
    """
    messages = [{"role": "system", "content": "문장에 담긴 감정을 알려줘."}]
    if with_examples:
        for sentence, label in SENTIMENT_EXAMPLES:
            messages.append({"role": "user", "content": sentence})
            messages.append({"role": "assistant", "content": label})
    messages.append({"role": "user", "content": text})
    return messages


def call(provider: str, messages: list[dict]):
    """한 프로바이더로 호출한다. 모델 문자열만 다를 뿐 호출 코드는 같다."""
    import litellm

    return litellm.completion(
        model=model_for(provider),
        messages=messages,
        timeout=60,
        **api_base_kwargs(provider),
    )


def _answer(resp) -> str:
    return resp.choices[0].message.content.strip().replace("\n", " ")


def demo_bare_vs_designed(providers: list[str]) -> None:
    """같은 입력을 빈약한 프롬프트와 설계된 프롬프트로 보내 출력을 비교한다."""
    print("=== 1. 빈약한 vs 설계된 프롬프트 — 문의 분류 ===")
    text = "어제 주문한 물건이 아직도 안 왔어요."
    print(f"입력: {text}")
    for provider in providers:
        print(f"\n[{provider}]")
        bare = call(provider, bare_classify(text))
        designed = call(provider, designed_classify(text))
        print(f"  빈약: {_answer(bare)}")
        print(f"  설계: {_answer(designed)}")


def demo_fewshot(providers: list[str]) -> None:
    """경계 사례를 zero-shot과 few-shot으로 보내 안정성을 비교한다."""
    print("\n\n=== 2. few-shot 효과 — 경계 사례 감정 분류 ===")
    text = "가격은 그냥 무난한 것 같습니다."
    print(f"입력: {text}")
    for provider in providers:
        print(f"\n[{provider}]")
        zero = call(provider, sentiment_messages(text, with_examples=False))
        few = call(provider, sentiment_messages(text, with_examples=True))
        print(f"  zero-shot: {_answer(zero)}")
        print(f"  few-shot:  {_answer(few)}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    providers = target_providers(available_providers())
    if not providers:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    demo_bare_vs_designed(providers)
    demo_fewshot(providers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
