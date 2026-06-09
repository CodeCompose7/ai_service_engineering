"""lec07 웹 앱 스모크 테스트.

페이지가 뜨는지만 확인한다. /api/query·/api/eval은 임베딩·LLM이 필요해 무거우므로
브라우저나 예제 실행으로 확인한다.
"""

from starlette.testclient import TestClient

from section2.lec07.app import app


def test_index_page_serves_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "mini RAG" in response.text
    assert "EVAL_SET" in response.text
