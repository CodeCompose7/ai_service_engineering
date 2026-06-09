"""lec01 — function calling 원리.

LLM은 모르는 것이 있고(실시간 값), 잘 못하는 것이 있고(큰 수의 정확한 계산), 직접 할 수
없는 일이 있다(바깥 세계에 대한 조회·행동). function calling은 모델에 도구 목록을 주고,
모델이 필요할 때 어떤 도구를 어떤 인자로 부를지 스스로 정하게 한다. 그 요청을 받아 실제로
실행하는 것은 우리 코드다. 모델은 실행하지 않고 요청만 한다.

한 바퀴는 이렇다.
  질문 → 모델: 도구 호출 요청(tool_calls) → 우리가 실행 → 결과를 모델에 전달 → 모델: 최종 답
모델이 결과를 받고 또 부를 수도 있어, 도구 호출이 멈출 때까지 도는 loop로 둔다.

도구는 tools/ 폴더에 한 파일씩 두고, tools 패키지가 모아 TOOLS(스키마 목록)와 run_tool
(이름→실행)로 내보낸다. 여기 fc.py는 호출 loop만 맡는다.

호출은 S1·S2처럼 LiteLLM을 경유한다. tool calling의 신뢰성은 모델마다 다르고 로컬 모델은
약한 편이라(lec06에서 다룬다), 기초인 여기서는 안정적인 클라우드 프로바이더를 앞세운다.

실행:
    uv run python src/section3/lec01/fc.py
"""

import json
import os

from section3.lec01.tools import TOOLS, run_tool

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
    """tool calling이 안정적인 클라우드 프로바이더를 우선 고른다. 없으면 로컬 Ollama로 폴백한다."""
    env = os.environ if env is None else env
    for name, key in CLOUD_KEY_ENV.items():
        if env.get(key):
            return DEFAULT_MODELS[name], {}
    if env.get("OLLAMA_API_BASE"):
        model = f"ollama/{env.get('OLLAMA_MODEL', 'gemma4:12b')}"
        return model, {"api_base": env.get("OLLAMA_API_BASE")}
    raise RuntimeError("준비된 프로바이더가 없습니다. .env에 키를 넣거나 Ollama를 띄우세요.")


def chat(question: str, max_steps: int = 5) -> dict:
    """질문을 모델에 보내고, 도구 호출이 멈출 때까지 실행·전달을 반복해 최종 답을 받는다."""
    import litellm

    model, kwargs = resolve_model()
    messages = [{"role": "user", "content": question}]
    trace = []
    for _ in range(max_steps):
        resp = litellm.completion(model=model, messages=messages, tools=TOOLS, **kwargs)
        msg = resp.choices[0].message
        messages.append(msg.model_dump())
        if not msg.tool_calls:
            return {"answer": msg.content, "model": model, "trace": trace}
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = run_tool(call.function.name, args)
            trace.append({"name": call.function.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return {"answer": None, "model": model, "trace": trace}


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    questions = [
        "73654 곱하기 8921은 얼마야?",
        "지금 몇 시인지 알려줘.",
        "RAG가 뭐야? 한 문장으로.",
        "안녕! 한 문장으로 인사해줘.",
    ]
    for question in questions:
        print(f"질문: {question}")
        result = chat(question)
        if result["trace"]:
            for step in result["trace"]:
                print(f"  → 도구 호출: {step['name']}({step['args']}) = {step['result']}")
        else:
            print("  → 도구 호출 없음 (모델이 직접 답함)")
        print(f"  답 ({result['model']}): {result['answer']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
