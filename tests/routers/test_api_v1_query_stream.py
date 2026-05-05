import json

from fastapi.testclient import TestClient
import pytest

from main import app
from routers import api_v1


@pytest.fixture
def client(monkeypatch):
    class TokenInfo:
        remaining_queries = 123
        total_queries = 10
        success_queries = 9

    app.dependency_overrides.clear()
    app.dependency_overrides[api_v1.verify_api_token] = lambda: TokenInfo()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_query_without_stream_returns_json(client, monkeypatch):
    monkeypatch.setattr(
        api_v1.question_service,
        "search_similar_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        api_v1.ai_service,
        "generate_answer",
        lambda *args, **kwargs: "A",
    )

    response = client.get(
        "/api/v1/query",
        params={"token": "demo", "title": "题目", "stream": "false"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["code"] == 1
    assert body["data"]["answer"] == "A"


def test_query_with_stream_returns_event_stream(client, monkeypatch):
    monkeypatch.setattr(
        api_v1.question_service,
        "search_similar_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        api_v1.ai_service,
        "generate_answer",
        lambda *args, **kwargs: "A",
    )

    with client.stream(
        "GET",
        "/api/v1/query",
        params={"token": "demo", "title": "题目", "stream": "true"},
    ) as response:
        body = b"".join(response.iter_raw())

    assert response.status_code == 200


def test_streaming_query_emits_heartbeat_before_result(client, monkeypatch):
    real_wait = api_v1.asyncio.wait
    state = {"count": 0}

    async def slow_execute_query(*args, **kwargs):
        from schemas.v1 import QueryResponse, SingleResultData

        return QueryResponse(
            code=1,
            message="请求成功",
            data=SingleResultData(
                question="题目",
                answer="A",
                times=123,
                ai=True,
            ),
        )

    async def fake_wait(tasks, timeout=None):
        state["count"] += 1
        if state["count"] == 1:
            return set(), set(tasks)
        return await real_wait(tasks, timeout=0)

    monkeypatch.setattr(api_v1, "_execute_query", slow_execute_query)
    monkeypatch.setattr(api_v1.asyncio, "wait", fake_wait)

    with client.stream(
        "GET",
        "/api/v1/query",
        params={"token": "demo", "title": "题目", "stream": "true"},
    ) as response:
        text = b"".join(response.iter_raw()).decode("utf-8")

    assert "event: heartbeat" in text
    assert "event: result" in text
    assert text.index("event: heartbeat") < text.index("event: result")



def test_streaming_query_emits_terminal_error_result(client, monkeypatch):
    async def failing_execute_query(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(api_v1, "_execute_query", failing_execute_query)

    with client.stream(
        "GET",
        "/api/v1/query",
        params={"token": "demo", "title": "题目", "stream": "true"},
    ) as response:
        text = b"".join(response.iter_raw()).decode("utf-8")

    assert "event: result" in text
    payload = text.split("data: ", 1)[1].strip()
    body = json.loads(payload)
    assert body["code"] == 500
    assert "provider down" in body["message"]
