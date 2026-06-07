"""lec03 — 설정한 프로바이더에게 한 번 물어보는 간단한 스크립트.

sampling_compare.py는 파라미터 효과를 보려고 같은 질문을 여러 번 호출한다. 하지만
그냥 한 번 물어보고 답만 받고 싶을 때가 더 많다. 이 스크립트는 .env의
DEFAULT_PROVIDER(없으면 준비된 첫 프로바이더)로 한 번 호출해 답만 출력한다.
temperature·top_p·top_k를 옵션으로 줄 수 있고, 프로바이더가 못 받는 값은 자동으로
보정한다. OpenAI는 top_k를 빼고, Anthropic은 temperature 상한을 적용한다.

탐지·모델 구성·파라미터 보정 로직은 sampling_compare에서 그대로 가져다 쓴다.

실행:
    uv run python src/section1/lec03/ask.py
    uv run python src/section1/lec03/ask.py "원하는 질문을 여기에"
    uv run python src/section1/lec03/ask.py -t 0.2 "원하는 질문"
    uv run python src/section1/lec03/ask.py -t 1.5 --top-p 0.9 --top-k 40 "원하는 질문"
"""

import argparse
import os

# 스크립트로 직접 실행하면 이 파일이 있는 디렉터리가 sys.path에 올라가므로 형제 모듈로 import한다.
from sampling_compare import (
    api_base_kwargs,
    available_providers,
    model_for,
    provider_order,
    safe_sampling_kwargs,
)

DEFAULT_QUESTION = "바다를 묘사하는 짧은 문장을 지어줘."


def parse_args() -> argparse.Namespace:
    """질문과 샘플링 옵션을 파싱한다."""
    parser = argparse.ArgumentParser(description="설정한 프로바이더에게 한 번 물어본다.")
    parser.add_argument("question", nargs="*", help="물어볼 질문 (없으면 기본 질문)")
    parser.add_argument(
        "-t", "--temperature", type=float, default=None, help="샘플링 온도"
    )
    parser.add_argument("--top-p", dest="top_p", type=float, default=None, help="top_p")
    parser.add_argument(
        "--top-k",
        dest="top_k",
        type=int,
        default=None,
        help="top_k (OpenAI는 미지원이라 자동 제거)",
    )
    return parser.parse_args()


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    args = parse_args()
    order = provider_order(os.environ.get("DEFAULT_PROVIDER"), available_providers())
    if not order:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    # 인자로 질문을 주면 그걸 쓰고, 없으면 기본 질문을 쓴다.
    question = " ".join(args.question).strip() or DEFAULT_QUESTION
    provider = order[0]
    model = model_for(provider)
    # 준 샘플링 값을 프로바이더가 받을 수 있는 형태로 보정한다.
    sampling = safe_sampling_kwargs(
        provider, temperature=args.temperature, top_p=args.top_p, top_k=args.top_k
    )

    # LiteLLM은 무거운 의존성이라 실제 호출 직전에 import 한다.
    import litellm

    messages = [{"role": "user", "content": question}]
    try:
        # 일부 모델이 멈추는 경우를 대비해 timeout을 둔다.
        resp = litellm.completion(
            model=model,
            messages=messages,
            timeout=60,
            **api_base_kwargs(provider),
            **sampling,
        )
    except Exception as exc:
        print(f"호출 실패: {type(exc).__name__} — {exc}")
        return 1

    header = f"[{provider} / {model}]"
    if sampling:
        header += f"  {sampling}"
    print(header)
    print(resp.choices[0].message.content.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
