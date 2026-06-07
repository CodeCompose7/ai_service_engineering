"""lec04 — 첫 호출과 메시지 구조.

같은 코드를 클라우드(gemini)와 로컬(ollama) 두 백엔드로 돌려, 첫 LLM 호출이 어떻게
구성되고 응답에서 무엇을 꺼내는지 본다. 모델 문자열만 다를 뿐 호출 코드는 같다.

세 가지를 보여준다.

1. 첫 호출: system+user 메시지로 답을 받고, 본문·토큰 수·종료 이유를 꺼낸다.
2. system 메시지: 같은 질문에 system만 바꿔 답이 어떻게 달라지는지 본다.
3. 멀티턴: 모델은 대화를 스스로 기억하지 않으므로, 이전 대화를 직접 실어 줘야 이어진다.

모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec04/first_call.py
"""

import argparse
import os
import time

# 이 단위의 기준 백엔드. 클라우드 gemini와 로컬 ollama를 같은 코드로 돌려 비교한다.
DEFAULT_MODELS = {
    "gemini": "gemini/gemini-2.5-flash",
}
CLOUD_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
}
TARGET_ORDER = ["gemini", "ollama"]


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


def build_messages(system: str | None, user: str) -> list[dict]:
    """system과 user 한 쌍으로 messages 목록을 만든다. system이 없으면 user만 담는다."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    return messages


def conversation(turns: list[tuple[str, str]]) -> list[dict]:
    """(role, content) 쌍의 목록을 messages 목록으로 펼친다. 멀티턴 대화를 직접 만든다."""
    return [{"role": role, "content": content} for role, content in turns]


def call(provider: str, messages: list[dict]):
    """한 프로바이더로 호출한다. 모델 문자열만 다를 뿐 호출 코드는 어디서나 같다."""
    import litellm

    return litellm.completion(
        model=model_for(provider),
        messages=messages,
        timeout=60,
        **api_base_kwargs(provider),
    )


def usage_line(resp) -> str:
    """응답의 토큰 사용량을 한 줄로 만든다. 일부 백엔드는 값이 없을 수 있다."""
    u = getattr(resp, "usage", None)
    if not u:
        return "usage 정보 없음"
    return f"prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}"


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def demo_first_call(providers: list[str]) -> None:
    """같은 메시지를 두 백엔드로 보내 본문·토큰 수·종료 이유를 나란히 본다."""
    print("=== 1. 첫 호출 — 같은 메시지, 두 백엔드 ===")
    messages = build_messages("너는 간결하게 답하는 도우미야.", "한 문장으로 자기소개를 해줘.")
    for provider in providers:
        resp = call(provider, messages)
        print(f"\n[{provider} / {model_for(provider)}]")
        print(f"  본문: {_oneline(resp.choices[0].message.content)}")
        print(f"  usage: {usage_line(resp)}")
        print(f"  finish_reason: {resp.choices[0].finish_reason}")


def demo_system_message(providers: list[str]) -> None:
    """같은 질문에 system만 바꿔 답이 어떻게 달라지는지 본다."""
    print("\n\n=== 2. system 메시지의 힘 — 같은 질문, 다른 지시 ===")
    user = "LiteLLM이 뭐야?"
    systems = {
        "간결": "한 문장으로만 답해.",
        "초등학생용": "초등학생도 알 수 있게 아주 쉬운 말로 두 문장 안에 설명해.",
    }
    for provider in providers:
        print(f"\n[{provider}]")
        for label, system in systems.items():
            resp = call(provider, build_messages(system, user))
            print(f"  ({label}) {_oneline(resp.choices[0].message.content)}")


def demo_multiturn(providers: list[str]) -> None:
    """모델은 스스로 기억하지 않는다. 이전 대화를 실어 줄 때만 맥락이 이어진다."""
    print("\n\n=== 3. 멀티턴 — 모델은 스스로 기억하지 않는다 ===")
    follow_up = "내 이름이 뭐라고 했지?"
    for provider in providers:
        print(f"\n[{provider}]")
        # 이전 대화 없이 후속 질문만 보내면 모델은 알 수가 없다.
        r1 = call(provider, build_messages(None, follow_up))
        print(f"  이전 대화 없이: {_oneline(r1.choices[0].message.content)}")
        # 이전 대화를 messages에 직접 실어 주면 맥락이 이어진다.
        r2 = call(
            provider,
            conversation(
                [
                    ("user", "내 이름은 Alice야."),
                    ("assistant", "반가워요, Alice!"),
                    ("user", follow_up),
                ]
            ),
        )
        print(f"  이전 대화를 실으면: {_oneline(r2.choices[0].message.content)}")


def measure(provider: str, messages: list[dict], rounds: int = 3) -> float:
    """같은 호출을 여러 번 보내 평균 응답 시간(초)을 잰다."""
    elapsed = []
    for _ in range(rounds):
        start = time.perf_counter()
        call(provider, messages)
        elapsed.append(time.perf_counter() - start)
    return sum(elapsed) / len(elapsed)


def demo_latency(providers: list[str]) -> None:
    """같은 호출의 응답 시간을 백엔드별로 재서 클라우드와 로컬의 속도 차를 본다."""
    print("=== (선택) 호출 지연 비교 — 같은 호출의 평균 응답 시간 ===")
    messages = build_messages("너는 간결하게 답하는 도우미야.", "한 문장으로 자기소개를 해줘.")
    for provider in providers:
        avg = measure(provider, messages)
        print(f"  {provider:8s} 평균 {avg:.2f}초   ({model_for(provider)})")


def parse_args() -> argparse.Namespace:
    """실행 옵션을 파싱한다."""
    parser = argparse.ArgumentParser(description="첫 호출과 메시지 구조 예제.")
    parser.add_argument(
        "--latency",
        action="store_true",
        help="(선택) 핵심 데모 대신 호출 지연만 비교한다",
    )
    return parser.parse_args()


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    args = parse_args()
    providers = target_providers(available_providers())
    if not providers:
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    # (선택) 지연 비교만 따로 돌린다.
    if args.latency:
        demo_latency(providers)
        return 0

    demo_first_call(providers)
    demo_system_message(providers)
    demo_multiturn(providers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
