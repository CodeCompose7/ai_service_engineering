"""lec03 — 설정한 프로바이더에게 한 번 물어보는 간단한 스크립트.

sampling_compare.py는 파라미터 효과를 보려고 같은 질문을 여러 번 호출한다. 하지만
그냥 한 번 물어보고 답만 받고 싶을 때가 더 많다. 이 스크립트는 .env의
DEFAULT_PROVIDER(없으면 준비된 첫 프로바이더)로 한 번 호출해 답만 출력한다.
샘플링 파라미터는 따로 주지 않아 모델 기본값으로 답한다.

탐지·모델 구성 로직은 sampling_compare에서 그대로 가져다 쓴다.

실행:
    uv run python src/section1/lec03/ask.py
    uv run python src/section1/lec03/ask.py "원하는 질문을 여기에"
"""

import os
import sys

# 스크립트로 직접 실행하면 이 파일이 있는 디렉터리가 sys.path에 올라가므로 형제 모듈로 import한다.
from sampling_compare import (
    api_base_kwargs,
    available_providers,
    model_for,
    provider_order,
)

DEFAULT_QUESTION = "바다를 묘사하는 짧은 문장을 지어줘."


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    order = provider_order(os.environ.get("DEFAULT_PROVIDER"), available_providers())
    if not order:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    # 인자로 질문을 주면 그걸 쓰고, 없으면 기본 질문을 쓴다.
    question = " ".join(sys.argv[1:]).strip() or DEFAULT_QUESTION
    provider = order[0]
    model = model_for(provider)

    # LiteLLM은 무거운 의존성이라 실제 호출 직전에 import 한다.
    import litellm

    messages = [{"role": "user", "content": question}]
    try:
        resp = litellm.completion(
            model=model, messages=messages, **api_base_kwargs(provider)
        )
    except Exception as exc:
        print(f"호출 실패: {type(exc).__name__} — {exc}")
        return 1

    print(f"[{provider} / {model}]")
    print(resp.choices[0].message.content.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
