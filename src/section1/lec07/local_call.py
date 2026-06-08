"""lec07 — Ollama 로컬.

클라우드와 똑같은 코드로 로컬 모델을 부른다. 달라지는 것은 모델 문자열(ollama/...)과
호스트 주소(api_base)뿐이다. 같은 프롬프트를 클라우드와 로컬에 보내 본문·속도·형식
준수를 나란히 비교한다.

두 가지를 보여준다.

1. 같은 질문: 본문 품질과 응답 시간이 어떻게 다른지 본다.
2. 형식 지시: 까다로운 형식을 줬을 때 로컬이 더 자주 흐트러지는지 본다.

모든 호출은 LiteLLM을 경유한다.

실행:
    uv run python src/section1/lec07/local_call.py
"""

import os
import time

CLOUD_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_LOCAL_MODEL = "gemma4:12b"


def have_cloud(env: dict | None = None) -> bool:
    """클라우드(gemini) 키가 있는지."""
    env = os.environ if env is None else env
    return bool(env.get("GEMINI_API_KEY"))


def have_local(env: dict | None = None) -> bool:
    """로컬 Ollama 주소가 있는지."""
    env = os.environ if env is None else env
    return bool(env.get("OLLAMA_API_BASE"))


def local_model(env: dict | None = None) -> str:
    """로컬 모델 문자열. ollama/<모델> 형식."""
    env = os.environ if env is None else env
    return f"ollama/{env.get('OLLAMA_MODEL', DEFAULT_LOCAL_MODEL)}"


def ollama_kwargs(env: dict | None = None) -> dict:
    """로컬 호출에 더 넘기는 인자. 호스트 주소만 필요하다."""
    env = os.environ if env is None else env
    return {"api_base": env.get("OLLAMA_API_BASE")}


def targets(env: dict | None = None) -> list[tuple[str, str, dict]]:
    """(라벨, 모델 문자열, 추가 kwargs) 목록. 준비된 클라우드·로컬만 담는다."""
    env = os.environ if env is None else env
    out: list[tuple[str, str, dict]] = []
    if have_cloud(env):
        out.append(("클라우드", CLOUD_MODEL, {}))
    if have_local(env):
        out.append(("로컬", local_model(env), ollama_kwargs(env)))
    return out


def timed_call(model: str, messages: list[dict], **kwargs) -> tuple[str, float]:
    """호출하고 (본문, 걸린 시간 초)을 돌려준다."""
    import litellm

    start = time.perf_counter()
    resp = litellm.completion(model=model, messages=messages, timeout=120, **kwargs)
    elapsed = time.perf_counter() - start
    return resp.choices[0].message.content, elapsed


def _oneline(text: str) -> str:
    return text.strip().replace("\n", " ")


def compare(env: dict, title: str, prompt: str) -> None:
    """같은 프롬프트를 준비된 백엔드마다 보내 본문·시간을 나란히 출력한다."""
    print(f"=== {title} ===")
    print(f"프롬프트: {prompt}")
    messages = [{"role": "user", "content": prompt}]
    for label, model, kwargs in targets(env):
        try:
            text, elapsed = timed_call(model, messages, **kwargs)
        except Exception as exc:
            print(f"\n  [{label}] {model}")
            print(f"    실패: {type(exc).__name__} — 연결을 확인하세요")
            continue
        print(f"\n  [{label}] {model}  ({elapsed:.1f}초)")
        print(f"    {_oneline(text)}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    if not targets():
        print("gemini 키나 ollama 중 하나가 필요합니다. .env를 확인하세요.")
        return 1

    compare(
        os.environ,
        "1. 같은 질문 — 클라우드 vs 로컬",
        "AI 서비스 엔지니어링을 한 문장으로 설명해줘.",
    )
    print("\n")
    compare(
        os.environ,
        "2. 형식 지시 — 마크다운·설명 없이 한 문장만",
        "마크다운이나 군더더기 없이 딱 한 문장으로만 답해. 바다가 파란 이유는?",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
