"""S4 lec03 — 상태와 가드를 끼운 하네스 (assistant.py).

lec02 하네스 골격에, lec03의 상태(SessionStore)와 가드레일(행동·출력·PII)을 실제로 끼운 예제다.
state.py·guard.py가 부품이라면, 여기서는 그 부품들을 한 흐름으로 엮는다.

한 번의 처리:
    상태 load → 행동 검사 → (허용이면) 모델 실행 → 출력 검증 → PII 마스킹 → 상태 save
    (막히면) 거부하고 멈춤

출력은 구조화(JSON)로 받아 Pydantic 계약으로 검증한다. lec02 Harness._parse_action을 재사용해
지저분한 출력에서 JSON을 건진다.

실행:
    uv run python src/section4/lec03/assistant.py
"""

import asyncio

from section3.lec02.async_llm import acomplete
from section4.lec02.harness import GuardError, Harness
from section4.lec03.guard import Reply, check_action, decide_action, redact_pii, validate_output
from section4.lec03.state import SessionState, SessionStore

RESPONDER = (
    "너는 고객 지원 도우미다. 주어진 사용자 정보와 요청을 보고 답한다. "
    '반드시 {"answer": "한국어 답", "confidence": 0과 1 사이 숫자} 형식의 JSON만 출력해라.'
)
EXTRACTOR = (
    "사용자 발화에서 사용자에 관한 새 사실(이름·플랜·이메일 등)을 뽑아라. "
    '{"키": "값"} 형식 JSON으로, 새 사실이 없으면 {} 만 출력해라.'
)


class GuardedAssistant:
    """상태와 가드레일을 끼운 하네스. 기억하고, 검사하고, 응답을 다듬어 내보낸다."""

    def __init__(self, store: SessionStore | None = None):
        self.store = store or SessionStore()

    async def handle(self, session_id: str, request: str) -> dict:
        state = self.store.load(session_id)  # 상태 load
        state.turns += 1
        trace = [f"load(turns={state.turns})"]

        action = await decide_action(request)  # 자연어 → 행동
        trace.append(f"행동={action}")
        try:
            check_action(action)  # 허용 행동 제약
        except GuardError:
            trace.append("막힘")
            self.store.save(state)
            return {"reply": f"그 요청({action})은 허용되지 않습니다.", "trace": trace}

        learned = await self._extract_facts(request)  # 대화에서 새 사실을 배운다
        if learned:
            state.facts.update(learned)
            trace.append(f"기억={learned}")

        reply = await self._respond(state, request)  # 모델 실행 + 출력 검증
        trace.append(f"검증 통과(conf={reply.confidence})")
        safe = redact_pii(reply.answer)  # PII 마스킹
        trace.append("PII 마스킹")
        self.store.save(state)  # 갱신된 facts + turns 저장
        trace.append("save")
        return {"reply": safe, "confidence": reply.confidence, "trace": trace}

    async def _extract_facts(self, request: str) -> dict:
        """발화에서 사용자에 관한 새 사실을 뽑아 dict로 돌려준다. 없으면 빈 dict."""
        raw = await acomplete([
            {"role": "system", "content": EXTRACTOR},
            {"role": "user", "content": request},
        ])
        data = Harness._parse_action(raw)
        return data if isinstance(data, dict) else {}

    async def _respond(self, state, request: str) -> Reply:
        facts = ", ".join(f"{k}={v}" for k, v in state.facts.items()) or "(없음)"
        raw = await acomplete([
            {"role": "system", "content": RESPONDER},
            {"role": "user", "content": f"사용자 정보: {facts}\n요청: {request}"},
        ])
        data = Harness._parse_action(raw) or {"answer": raw.strip(), "confidence": 0.5}
        try:
            return validate_output(data)
        except GuardError:
            # 계약을 어기면 안전한 기본값으로 떨어진다. 깨진 출력을 그대로 내보내지 않는다.
            return Reply(answer=str(data.get("answer", "답을 만들지 못했습니다")), confidence=0.0)


def _run(assistant: "GuardedAssistant", request: str) -> None:
    result = asyncio.run(assistant.handle("alice", request))
    print(f"요청: {request}")
    print(f"  답: {result['reply']}")
    print(f"  트레이스: {result['trace']}")


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    path = "/tmp/lec03_assistant"
    SessionStore(path).save(SessionState("alice"))  # 빈 상태로 시작

    print("=== 1) 사용자가 사실을 알려줌 (에이전트가 배워서 저장) ===")
    first = GuardedAssistant(SessionStore(path))
    _run(first, "나는 Alice이고 방금 Pro 플랜으로 업그레이드했어. 이메일은 alice@corp.com이야.")
    print(f"   디스크에 저장된 facts: {SessionStore(path).load('alice').facts}\n")

    print("=== 2) 프로세스 재시작 (새 store·새 assistant) ===")
    revived = GuardedAssistant(SessionStore(path))
    _run(revived, "내 플랜이 뭐였는지랑 이메일 알려줘")  # 재시작 후에도 배운 사실을 기억
    _run(revived, "내 계정을 삭제해줘")  # 가드: 막힘
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
