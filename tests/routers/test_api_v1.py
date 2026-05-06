from types import SimpleNamespace

import pytest

import routers.api_v1 as api_v1


def _payload(response):
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return response.dict()


@pytest.mark.asyncio
async def test_query_question_uses_query_request_helpers_and_keeps_single_result_shape(
    monkeypatch,
):
    token_info = SimpleNamespace(remaining_queries=9)
    calls = {}

    class FakeQueryRequest:
        def __init__(self, **kwargs):
            calls["request_kwargs"] = kwargs
            self.type = kwargs.get("type")
            self.subject = kwargs.get("subject")
            self.more = kwargs.get("more")
            self.stream = kwargs.get("stream")

        def get_question_text(self):
            calls["question_text_called"] = True
            return "helper-selected title"

        def get_options_list(self):
            calls["options_list_called"] = True
            return [
                "A. ![img](https://img.test/a.png)",
                "B. 普通选项",
            ]

    monkeypatch.setattr(api_v1, "QueryRequest", FakeQueryRequest)
    monkeypatch.setattr(
        api_v1.question_service,
        "search_similar_questions",
        lambda **kwargs: [],
    )

    def fake_generate_answer(query_text, options_list, question_type, subject):
        calls["generate_answer_args"] = (query_text, options_list, question_type, subject)
        return "A"

    monkeypatch.setattr(api_v1.ai_service, "generate_answer", fake_generate_answer)

    response = await api_v1.query_question(
        token_info=token_info,
        title="manual title",
        q="manual q",
        question="manual question",
        options="manual options should not be parsed directly",
        type="single",
        subject=None,
        more=False,
        force_ai=False,
        stream=False,
    )

    assert calls["request_kwargs"] == {
        "title": "manual title",
        "q": "manual q",
        "question": "manual question",
        "options": "manual options should not be parsed directly",
        "type": "single",
        "subject": None,
        "more": False,
        "stream": False,
    }
    assert calls["question_text_called"] is True
    assert calls["options_list_called"] is True
    assert calls["generate_answer_args"] == (
        "helper-selected title",
        [
            "A. ![img](https://img.test/a.png)",
            "B. 普通选项",
        ],
        "single",
        None,
    )
    assert _payload(response) == {
        "code": 1,
        "message": "请求成功",
        "data": {
            "question": "helper-selected title",
            "answer": "A",
            "times": 9,
            "ai": True,
        },
    }


@pytest.mark.asyncio
async def test_query_question_prefers_title_over_q_and_question(monkeypatch):
    token_info = SimpleNamespace(remaining_queries=3)
    calls = {}

    monkeypatch.setattr(
        api_v1.question_service,
        "search_similar_questions",
        lambda **kwargs: [],
    )

    def fake_generate_answer(query_text, options_list, question_type, subject):
        calls["generate_answer_args"] = (query_text, options_list, question_type, subject)
        return "B"

    monkeypatch.setattr(api_v1.ai_service, "generate_answer", fake_generate_answer)

    response = await api_v1.query_question(
        token_info=token_info,
        title="title wins",
        q="q loses",
        question="question loses",
        options="A. 甲\nB. 乙",
        type="single",
        subject=None,
        more=False,
        force_ai=False,
        stream=False,
    )

    assert calls["generate_answer_args"] == (
        "title wins",
        ["A. 甲", "B. 乙"],
        "single",
        None,
    )
    assert _payload(response) == {
        "code": 1,
        "message": "请求成功",
        "data": {
            "question": "title wins",
            "answer": "B",
            "times": 3,
            "ai": True,
        },
    }
