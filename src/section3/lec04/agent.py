"""lec04 — MCP 연결 에이전트.

도구를 에이전트 코드에 박지 않고, MCP 서버에 붙어 그 서버가 주는 도구를 쓴다. 흐름은 세 단계다.

1. 연결: stdio로 mcp_server.py를 자식 프로세스로 띄워 세션을 연다.
2. 발견: session.list_tools()로 서버의 도구 목록과 입력 스키마를 받아, function 스키마로 옮긴다.
3. 호출: 모델이 도구를 고르면 session.call_tool()로 서버에 위임하고, 결과를 다시 모델에 넣는다.

모델에게는 lec01~03과 똑같이 function calling으로 보인다. 다른 점은 도구의 구현과 목록이 우리 코드가
아니라 별도 서버에 있다는 것이다. 호출은 lec02 async_llm을 쓴다.

실행:
    uv run python src/section3/lec04/agent.py
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from section3.lec01.llm import resolve_model
from section3.lec02.async_llm import acompletion, call_count, reset_calls

SERVER = StdioServerParameters(command=sys.executable, args=["src/section3/lec04/mcp_server.py"])
SYSTEM = (
    "너는 메모 도구를 쓰는 도우미다. 요청에 맞춰 메모를 저장하거나 목록을 보여준다. "
    "도구 결과만 근거로 한국어로 답한다."
)


def _to_schema(tool) -> dict:
    """MCP 도구를 LiteLLM function 스키마로 바꾼다. inputSchema가 곧 parameters다."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def _result_text(result) -> str:
    """call_tool 결과에서 텍스트를 모은다."""
    return "\n".join(c.text for c in result.content if getattr(c, "type", None) == "text")


async def run_agent(task: str, max_steps: int = 10) -> dict:
    """MCP 서버에 붙어 도구를 발견하고, 모델이 고른 도구를 서버에 위임해 작업을 끝낸다."""
    reset_calls()
    model, kwargs = resolve_model()
    errlog = open(os.devnull, "w")  # 서버 로그는 흘려보낸다
    async with stdio_client(SERVER, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = [_to_schema(t) for t in listed.tools]
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": task},
            ]
            trace = []
            answer = None
            for _ in range(max_steps):
                msg = (await acompletion(model, messages, tools=tools, **kwargs)).choices[0].message
                messages.append(msg.model_dump())
                if not msg.tool_calls:
                    answer = msg.content
                    break
                for call in msg.tool_calls:
                    args = json.loads(call.function.arguments)
                    result = await session.call_tool(call.function.name, args)
                    trace.append({"name": call.function.name, "args": args})
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": _result_text(result)}
                    )
    errlog.close()
    return {
        "answer": answer,
        "model": model,
        "trace": trace,
        "llm_calls": call_count(),
        "discovered": [t.name for t in listed.tools],
    }


def _show(task: str, result: dict) -> None:
    print(f"질문: {task}")
    print(f"  발견한 MCP 도구: {result['discovered']}")
    for step in result["trace"]:
        shown = ", ".join(f"{k}={v}" for k, v in step["args"].items())
        print(f"  → call_tool {step['name']}({shown})")
    answer = str(result["answer"]).replace("\n", " ")
    print(f"  답 ({result['model']}): {answer}")
    print(f"  도구 {len(result['trace'])}번 · LLM {result['llm_calls']}회\n")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    task = "회의 메모로 'API 키 발급'과 '배포 일정 확인'을 저장하고, 전체 목록을 보여줘"
    _show(task, asyncio.run(run_agent(task)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
