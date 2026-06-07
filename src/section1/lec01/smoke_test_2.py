"""lec01 — 준비된 프로바이더 전체를 순차 호출하는 스모크 테스트.

smoke_test.py는 첫 성공에서 멈추지만, 이 스크립트는 .env에 준비된 프로바이더
(키가 채워진 클라우드 + base URL이 있는 Ollama)를 모두 차례로 호출해 각각의 응답과
성패를 한눈에 모아 보여준다. 네 프로바이더를 함께 준비했을 때 전부 닿는지 확인하는 용도다.
모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec01/smoke_test_2.py
"""

# 같은 폴더의 smoke_test에서 탐지·정렬·모델 구성 로직을 그대로 가져다 쓴다.
# 스크립트로 직접 실행하면 이 파일이 있는 디렉터리가 sys.path에 올라가므로 형제 모듈로 import한다.
from smoke_test import (
    available_providers,
    model_and_kwargs,
    provider_order,
)


def main() -> int:
    import os

    from dotenv import load_dotenv

    load_dotenv()

    default = os.environ.get("DEFAULT_PROVIDER")
    # smoke_test와 같은 탐지·정렬을 쓰되, 첫 성공에서 멈추지 않고 전부 돈다.
    order = provider_order(default, available_providers())

    if not order:
        print("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄운 뒤 다시 실행하세요.")
        return 1

    # LiteLLM은 무거운 의존성이라 실제 호출 직전에 import 한다.
    import litellm

    messages = [{"role": "user", "content": "한 문장으로 자기소개를 해줘."}]
    results: list[tuple[str, str, bool]] = []  # (provider, model, 성공 여부)

    for provider in order:
        model, kwargs = model_and_kwargs(provider)
        print(f"\n=== [{provider}] {model} ===")
        try:
            resp = litellm.completion(model=model, messages=messages, **kwargs)
        except Exception as exc:
            # 타입 이름만으로는 원인을 알 수 없으므로 프로바이더가 준 메시지도 함께 본다.
            print(f"  실패: {type(exc).__name__}")
            print(f"        {exc}")
            results.append((provider, model, False))
            continue
        print(resp.choices[0].message.content)
        results.append((provider, model, True))

    # 마지막에 프로바이더별 성패를 요약한다.
    print("\n--- 요약 ---")
    for provider, model, ok in results:
        mark = "성공" if ok else "실패"
        print(f"  {mark}  {provider:10s} {model}")

    ok_count = sum(1 for _, _, ok in results if ok)
    print(f"\n{len(results)}개 중 {ok_count}개 성공")
    # 하나라도 닿았으면 환경은 동작하는 것으로 본다.
    return 0 if ok_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
