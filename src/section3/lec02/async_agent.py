"""lec02 5.3절 — 비동기 도구 에이전트.

5절의 종착점이다. 도구도 루프도 async다. 모델이 한 턴에 독립적인 도구를 여러 개 요청하면
asyncio.gather로 동시에 실행한다. 동기 순차 버전(agent.py)과 같은 일을 하되, 독립 호출이 겹쳐
빠르다.

비동기 도구는 lec02/tools/search_wikipedia_async.py에 따로 두었다. lec01 도구는 lec01 강의용이다.
sync 루프(agent.py)와 견주어 보면, async로 가려면 도구뿐 아니라 루프까지 바꿔야 함이 드러난다.

실행:
    uv run python src/section3/lec02/async_agent.py
"""

import asyncio
import json

from section3.lec01.llm import acompletion, call_count, reset_calls, resolve_model
from section3.lec02.tools import SCHEMA as WIKI_SCHEMA
from section3.lec02.tools import search_wikipedia_async

WIKI_SYSTEM = (
    "너는 위키백과 검색 도구로 사실을 알아보는 도우미다. 여러 주제가 나오면 주제마다 "
    "search_wikipedia를 따로 부른다. 검색 결과만 근거로 한국어로 답하고 출처를 밝힌다."
)


async def _dispatch(_name: str, args: dict) -> str:  # 단일 도구라 이름은 보지 않는다
    return await search_wikipedia_async(**args)


async def run_agent_async(task, tools, dispatch, system, max_steps=10) -> dict:
    """async 에이전트 루프. 한 턴에 온 도구 호출들을 asyncio.gather로 동시에 실행한다."""
    reset_calls()
    model, kwargs = resolve_model()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    steps = []
    for _ in range(max_steps):
        resp = await acompletion(model, messages, tools=tools, **kwargs)
        msg = resp.choices[0].message
        messages.append(msg.model_dump())
        if not msg.tool_calls:
            return {
                "answer": msg.content,
                "model": model,
                "steps": steps,
                "llm_calls": call_count(),
            }
        parsed = [json.loads(c.function.arguments) for c in msg.tool_calls]
        # 같은 턴의 독립 호출을 한꺼번에 await한다.
        results = await asyncio.gather(
            *[dispatch(c.function.name, a) for c, a in zip(msg.tool_calls, parsed, strict=True)]
        )
        for call, args, result in zip(msg.tool_calls, parsed, results, strict=True):
            steps.append({"query": args.get("query")})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": str(result)})
    return {"answer": None, "model": model, "steps": steps, "llm_calls": call_count()}


async def wiki_agent_async(task: str) -> dict:
    return await run_agent_async(task, [WIKI_SCHEMA], _dispatch, WIKI_SYSTEM)


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    for task in [
        "에펠탑과 도쿄 타워는 각각 언제 지어졌나요?",
        "만리장성과 콜로세움은 각각 어느 나라에 있나요?",
    ]:
        result = asyncio.run(wiki_agent_async(task))
        print(f"작업: {task}")
        print(f"  검색: {[s['query'] for s in result['steps']]}")
        answer = str(result["answer"]).replace(chr(10), " ")[:90]
        print(f"  답 ({result['model']}): {answer}")
        print(f"  도구 {len(result['steps'])}번 · LLM {result['llm_calls']}회\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
