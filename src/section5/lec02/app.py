"""S5 lec02 — 통합 웹 서비스 (app.py).

채팅 웹 페이지와 관리자 페이지를 한 FastAPI 앱이 함께 제공한다. 프런트(HTML)도, 서버(API)도
한곳에서 낸다. 로컬에서 돌리고 API 키는 서버에만 있으니, 관리자 페이지는 채팅 화면의 링크
버튼으로 들어가는 것으로 충분하다.

- GET  /             채팅 페이지
- GET  /admin        관리자 페이지 (관찰 대시보드 + 설정)
- POST /chat         통합 어시스턴트(assistant.handle)를 부른다
- GET  /api/metrics  관찰 데이터(전체·사용자별·알림)와 현재 설정
- GET/POST /api/settings  가드 토글·RAG 토글을 읽고 바꾼다

실행:
    uv run uvicorn section5.lec02.app:app --reload
    그다음 브라우저에서 http://127.0.0.1:8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from section2.lec06.mini_rag import open_index
from section4.lec07.observe import check_alerts, metrics, metrics_by_user
from section5.lec02.assistant import Settings, Store, handle

WEB = Path(__file__).parent / "web"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user: str = "web"


class SettingsPatch(BaseModel):
    guard_injection: bool | None = None
    moderate: bool | None = None
    redact: bool | None = None
    rag: bool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """뜰 때 RAG 인덱스·관찰 보관소·설정을 준비한다. 인덱스가 없으면 RAG 없이 돈다."""
    from dotenv import load_dotenv

    load_dotenv()
    app.state.store = Store()
    app.state.settings = Settings()
    try:
        app.state.collection = open_index()
    except Exception:
        app.state.collection = None
    yield


app = FastAPI(title="통합 어시스턴트", lifespan=lifespan)


def _page(name: str) -> HTMLResponse:
    return HTMLResponse((WEB / name).read_text(encoding="utf-8"))


@app.get("/")
async def chat_page() -> HTMLResponse:
    return _page("chat.html")


@app.get("/admin")
async def admin_page() -> HTMLResponse:
    return _page("admin.html")


@app.post("/chat")
async def chat(req: ChatRequest) -> dict:
    try:
        return await handle(
            req.message,
            req.user,
            app.state.settings,
            app.state.store,
            app.state.collection,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"처리 실패: {exc}") from exc


@app.get("/api/metrics")
async def api_metrics() -> dict:
    store = app.state.store
    overall = metrics(store.traces)
    return {
        "overall": overall,
        "by_user": metrics_by_user(store.traces),
        "alerts": check_alerts(overall),
        "settings": vars(app.state.settings),
    }


@app.get("/api/settings")
async def get_settings() -> dict:
    return vars(app.state.settings)


@app.post("/api/settings")
async def set_settings(patch: SettingsPatch) -> dict:
    settings = app.state.settings
    for key, value in patch.model_dump(exclude_none=True).items():
        setattr(settings, key, value)
    return vars(settings)
