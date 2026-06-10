"""S4 lec03 세션 상태 테스트.

저장·불러오기와 인스턴스를 넘는 지속을 본다.
"""

from section4.lec03.state import SessionState, SessionStore


def test_save_and_load_roundtrip(tmp_path):
    store = SessionStore(tmp_path)
    store.save(SessionState("alice", facts={"plan": "Free"}, turns=1))
    loaded = store.load("alice")
    assert loaded.facts["plan"] == "Free"
    assert loaded.turns == 1


def test_persists_across_instances(tmp_path):
    SessionStore(tmp_path).save(SessionState("alice", facts={"plan": "Pro"}))
    # 새 인스턴스(프로세스 재시작)도 디스크에서 불러온다.
    loaded = SessionStore(tmp_path).load("alice")
    assert loaded.facts["plan"] == "Pro"


def test_unknown_session_starts_empty(tmp_path):
    state = SessionStore(tmp_path).load("nobody")
    assert state.facts == {}
    assert state.turns == 0
