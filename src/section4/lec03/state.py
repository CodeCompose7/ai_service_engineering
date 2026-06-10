"""S4 lec03 — 세션 간 상태 지속 (state.py).

컨텍스트 윈도우(lec01)는 한 번의 호출 안에서만 산다. 호출이 끝나면 사라진다. 그런데 서비스는
세션이 끊겼다 이어져도 사용자를 기억해야 한다. 그래서 상태를 윈도우 밖, 디스크에 둔다.

여기서는 세션 상태를 JSON 파일에 저장하는 작은 SessionStore를 만든다. 프로세스가 죽어도 다음
세션이 같은 session_id로 불러오면 사실이 그대로 살아 있다.

실행:
    uv run python src/section4/lec03/state.py
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_DIR = Path("/tmp/lec03_sessions")


@dataclass
class SessionState:
    """한 세션의 지속 상태. 사용자에 관한 사실과 누적 턴 수를 담는다."""

    session_id: str
    facts: dict = field(default_factory=dict)
    turns: int = 0


class SessionStore:
    """세션 상태를 JSON 파일로 저장해 프로세스가 죽어도 살아남게 한다."""

    def __init__(self, dir_path: Path | str = DEFAULT_DIR):
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def load(self, session_id: str) -> SessionState:
        """저장된 상태를 불러온다. 없으면 빈 상태로 시작한다."""
        path = self._path(session_id)
        if path.exists():
            return SessionState(**json.loads(path.read_text(encoding="utf-8")))
        return SessionState(session_id=session_id)

    def save(self, state: SessionState) -> None:
        """상태를 디스크에 쓴다."""
        self._path(state.session_id).write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8"
        )


def main() -> int:
    store = SessionStore()

    # 세션 1: 사용자가 자기 정보를 알려주면 사실로 쌓아 저장한다.
    state = store.load("alice")
    state.facts["name"] = "Alice"
    state.facts["plan"] = "Free"
    state.turns += 1
    store.save(state)
    print(f"세션 1 저장: facts={state.facts}, turns={state.turns}")

    # 프로세스가 죽었다 다시 떴다고 치자. 새 store 인스턴스가 디스크에서 불러온다.
    fresh_store = SessionStore()
    loaded = fresh_store.load("alice")
    print(f"재시작 후 불러옴: facts={loaded.facts}, turns={loaded.turns}")
    print(f"기억된 플랜: {loaded.facts.get('plan')}")

    # 새로운 세션 id는 빈 상태로 시작한다.
    other = fresh_store.load("bob")
    print(f"다른 세션(bob): facts={other.facts} (빈 상태로 시작)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
