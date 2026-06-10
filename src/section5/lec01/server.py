"""S5 lec01 — FastAPI 서빙 + 스트리밍 (server.py).

S1~S4에서 만든 기능을 그대로 감싸 API로 내보낸다. 여기서는 모델 호출(LiteLLM)을 감싸지만,
RAG·에이전트도 핸들러가 그 함수를 부르게 두면 똑같다. 그래서 서빙 코드는 얇다.

네 조각으로 본다.

- lifespan: 서버가 뜰 때 자원을 준비하고, 내릴 때 정리한다. 여기서는 모델을 한 번 정한다.
- 입력 검증: Pydantic 모델이 요청을 검사한다. 빈 질문·너무 긴 질문은 핸들러에 닿기
  전에 422로 막힌다.
- 에러 처리: 모델 호출이 실패하면 500이 아니라 502로 또렷이 알린다.
- 스트리밍: StreamingResponse로 토큰을 하나씩 흘려보낸다. 다 만들어 한 번에 주지 않는다.

실행:
    uv run python src/section5/lec01/server.py        # TestClient로 엔드포인트를 두드려 본다
    uv run uvicorn section5.lec01.server:app --reload  # 진짜 서버로 띄운다
"""

from contextlib import asynccontextmanager
from pathlib import Path

import litellm
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from section3.lec01.llm import resolve_model

WEB = Path(__file__).parent / "web"


class GenerateRequest(BaseModel):
    """요청 입력. Pydantic이 타입과 길이를 검사한다."""

    question: str = Field(min_length=1, max_length=2000)


async def run_completion(model: str, messages: list[dict], kwargs: dict) -> str:
    """비스트리밍 모델 호출. 테스트에서 가짜로 갈아끼운다."""
    response = await litellm.acompletion(model=model, messages=messages, **kwargs)
    return response.choices[0].message.content


async def run_stream(model: str, messages: list[dict], kwargs: dict):
    """스트리밍 모델 호출. 델타 토큰을 하나씩 내보낸다."""
    stream = await litellm.acompletion(model=model, messages=messages, stream=True, **kwargs)
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 수명. 뜰 때 모델을 정해 app.state에 둔다. 내릴 때 정리한다."""
    from dotenv import load_dotenv

    load_dotenv()
    app.state.model, app.state.kwargs = resolve_model()
    yield
    # 내릴 때 정리할 자원은 없다. 연결 풀 등을 닫는 자리.


app = FastAPI(title="추론 API", lifespan=lifespan)


@app.get("/")
async def index() -> HTMLResponse:
    """브라우저로 들어오면 보이는 테스트 페이지. /generate는 POST라 주소창으로는 못 부르니,
    질문을 입력해 두 엔드포인트를 눌러보는 작은 GET 화면을 띄운다."""
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))


@app.post("/generate")
async def generate(req: GenerateRequest) -> dict:
    """질문을 받아 답을 한 번에 돌려준다."""
    messages = [{"role": "user", "content": req.question}]
    try:
        answer = await run_completion(app.state.model, messages, app.state.kwargs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"모델 호출 실패: {exc}") from exc
    return {"answer": answer}


@app.post("/generate/stream")
async def generate_stream(req: GenerateRequest) -> StreamingResponse:
    """질문을 받아 답을 토큰 단위로 흘려보낸다."""
    messages = [{"role": "user", "content": req.question}]
    return StreamingResponse(
        run_stream(app.state.model, messages, app.state.kwargs),
        media_type="text/plain; charset=utf-8",
    )


def main() -> int:
    """TestClient로 세 가지를 두드려 본다. 정상·스트리밍·검증 실패."""
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        print("=== /generate (한 번에) ===")
        resp = client.post("/generate", json={"question": "한국의 수도는 어디인가요?"})
        print(f"  {resp.status_code} {resp.json()}")

        print("\n=== /generate/stream (토큰을 흘려보냄) ===  ", end="")
        with client.stream("POST", "/generate/stream", json={"question": "1부터 5까지 세줘"}) as s:
            for chunk in s.iter_text():
                print(chunk, end="", flush=True)
        print()

        print("\n=== 입력 검증 (빈 질문은 422로 막힘) ===")
        resp = client.post("/generate", json={"question": ""})
        print(f"  {resp.status_code} (검증 실패, 핸들러에 닿지 않음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
