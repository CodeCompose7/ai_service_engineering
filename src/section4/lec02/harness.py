"""S4 lec02 — 하네스 엔지니어링 (최소 하네스).

에이전트 = 모델 + 하네스. 모델 능력은 주어진 것으로 두고, 그 둘레의 하네스를 단단히 한다.
하네스는 제어 루프 + 도구 인터페이스 + 능력 감지 + 우아한 강등 + 실패 복구다.

- 능력 감지: litellm.supports_function_calling로 모델이 네이티브 도구 호출을 지원하는지 본다.
- 우아한 강등: 지원하면 네이티브 tool_calls 루프, 아니면 JSON 프롬프트 프로토콜로 같은 일을 한다.
- 실패는 시스템 문제: 모델이 JSON을 지저분하게 내도 파싱 가드로 건져내고, 안 되면 다시 묻는다.

같은 하네스가 강한 모델에서는 네이티브로, 약한 모델에서는 폴백으로 같은 과제를 끝낸다.

실행:
    uv run python src/section4/lec02/harness.py
"""

import asyncio
import json
import re

import litellm

from section3.lec01.tools.calculator import SCHEMA as CALC_SCHEMA
from section3.lec01.tools.calculator import calculate
from section3.lec02.async_llm import acompletion


class Harness:
    """모델 + 도구를 감싸는 최소 하네스. 능력을 감지해 네이티브와 폴백 경로를 고른다."""

    def __init__(self, model, tools, dispatch, max_steps=6, force_fallback=False):
        self.model = model
        self.tools = tools
        self.dispatch = dispatch
        self.max_steps = max_steps
        # 능력 감지: 강제 폴백이 아니고 모델이 네이티브 도구 호출을 지원하면 네이티브.
        self.native = (not force_fallback) and litellm.supports_function_calling(model)

    async def run(self, task: str) -> str:
        """능력에 따라 네이티브 또는 폴백 경로로 과제를 푼다."""
        return await (self._run_native(task) if self.native else self._run_fallback(task))

    async def _run_native(self, task: str) -> str:
        """네이티브 tool_calls 루프. 모델이 도구를 부르면 실행하고 결과를 돌려준다."""
        messages = [{"role": "user", "content": task}]
        for _ in range(self.max_steps):
            resp = await acompletion(self.model, messages, tools=self.tools)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content
            messages.append(msg)
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments)
                result = self.dispatch(call.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": str(result)}
                )
        return "(스텝 초과)"

    async def _run_fallback(self, task: str) -> str:
        """JSON 프롬프트 프로토콜. 네이티브 도구 호출이 없는 모델도 같은 일을 하게 한다."""
        messages = [
            {"role": "system", "content": self._fallback_system()},
            {"role": "user", "content": task},
        ]
        for _ in range(self.max_steps):
            resp = await acompletion(self.model, messages)
            raw = resp.choices[0].message.content
            action = self._parse_action(raw)
            if action is None:  # 파싱 실패는 시스템 문제 — 다시 묻는다.
                messages.append({"role": "user", "content": "JSON만 출력해라."})
                continue
            if "answer" in action:
                return action["answer"]
            name, args = action.get("tool"), action.get("args", {})
            result = self.dispatch(name, args)
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {"role": "user", "content": f"도구 {name} 결과: {result}. 다음 행동을 JSON으로."}
            )
        return "(스텝 초과)"

    def _fallback_system(self) -> str:
        """폴백 프로토콜을 설명하는 시스템 프롬프트를 도구 스키마로 만든다."""
        lines = []
        for tool in self.tools:
            fn = tool["function"]
            params = ", ".join(fn["parameters"]["properties"])
            lines.append(f"- {fn['name']}({params}): {fn['description']}")
        tools_desc = "\n".join(lines)
        return (
            "너는 도구를 쓸 수 있다. 사용할 도구:\n"
            f"{tools_desc}\n\n"
            '도구를 쓰려면 {"tool": "이름", "args": {...}} 형식의 JSON만 출력해라.\n'
            '답할 준비가 되면 {"answer": "..."} 형식의 JSON만 출력해라.\n'
            "JSON 외의 말은 하지 마라."
        )

    @staticmethod
    def _parse_action(raw: str) -> dict | None:
        """지저분한 출력에서 JSON 행동을 건져낸다. 마크다운 펜스·앞뒤 군더더기를 걷어낸다."""
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        block = re.search(r"\{.*\}", text, re.DOTALL)
        if not block:
            return None
        try:
            return json.loads(block.group(0))
        except json.JSONDecodeError:
            return None


def _dispatch(name: str, args: dict):
    """도구 이름을 실제 함수로 잇는다."""
    return {"calculate": calculate}[name](**args)


CANDIDATE_MODELS = [
    "gemini/gemini-2.5-flash",
    "openai/gpt-4o",
    "ollama/llama3.2",
    "ollama/gemma2:2b",
]
TASK = "3 곱하기 4를 계산하고, 그 결과에 10을 더하면 얼마야?"
MODEL = "gemini/gemini-2.5-flash"


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    print("=== 능력 감지 ===")
    for model in CANDIDATE_MODELS:
        native = litellm.supports_function_calling(model)
        print(f"  {model:30} → {'네이티브 도구 호출' if native else 'JSON 폴백'}")

    print(f"\n과제: {TASK}")
    native_h = Harness(MODEL, [CALC_SCHEMA], _dispatch)
    print(f"  감지된 경로: {'네이티브' if native_h.native else '폴백'}")
    print(f"  [네이티브]  {asyncio.run(native_h.run(TASK))}")
    fallback_h = Harness(MODEL, [CALC_SCHEMA], _dispatch, force_fallback=True)
    print(f"  [강등 JSON] {asyncio.run(fallback_h.run(TASK))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
