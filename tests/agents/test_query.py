from types import SimpleNamespace

import pytest

import agents.query as query_module
from agents.query import QueryAgent


def _set_completion(monkeypatch, handler):
    monkeypatch.setattr(query_module, "completion", SimpleNamespace(invoke=handler))


def test_answer_formats_options_as_newline_text_for_prompt(monkeypatch):
    agent = QueryAgent()
    captured = {}

    monkeypatch.setattr(
        query_module,
        "build_query_prompt",
        lambda question_type, title, options: captured.update(
            {
                "question_type": question_type,
                "title": title,
                "options": options,
            }
        )
        or "query-prompt",
    )
    _set_completion(monkeypatch, lambda prompt: "A")

    result = agent.answer(
        title="以下哪项正确？",
        options=["A. 甲", "B. 乙"],
        question_type="single",
    )

    assert result == "A"
    assert captured["options"] == "A. 甲\nB. 乙"


def test_answer_keeps_completion_path_when_option_image_refs_is_none(monkeypatch):
    agent = QueryAgent()
    calls = []

    monkeypatch.setattr(query_module, "build_query_prompt", lambda *args: "query-prompt")
    monkeypatch.setattr(
        QueryAgent,
        "_invoke_tool_agent",
        lambda self, prompt, image_tool: pytest.fail("tool path should not be used"),
        raising=False,
    )
    _set_completion(monkeypatch, lambda prompt: calls.append(prompt) or "A")

    result = agent.answer(
        title="以下哪项正确？",
        question_type="single",
        option_image_refs=None,
        image_tool=object(),
    )

    assert result == "A"
    assert calls == ["query-prompt"]


def test_answer_keeps_completion_path_when_option_image_refs_is_empty_dict(monkeypatch):
    agent = QueryAgent()
    calls = []

    monkeypatch.setattr(query_module, "build_query_prompt", lambda *args: "query-prompt")
    monkeypatch.setattr(
        QueryAgent,
        "_invoke_tool_agent",
        lambda self, prompt, image_tool: pytest.fail("tool path should not be used"),
        raising=False,
    )
    _set_completion(monkeypatch, lambda prompt: calls.append(prompt) or "A")

    result = agent.answer(
        title="以下哪项正确？",
        question_type="single",
        option_image_refs={},
        image_tool=object(),
    )

    assert result == "A"
    assert calls == ["query-prompt"]


def test_answer_uses_tool_path_when_image_refs_are_present(monkeypatch):
    agent = QueryAgent()
    captured = {}
    image_tool = object()

    monkeypatch.setattr(query_module, "build_query_prompt", lambda *args: "query-prompt")
    _set_completion(
        monkeypatch,
        lambda prompt: pytest.fail("completion path should not be used for image-backed options"),
    )

    def fake_invoke_tool_agent(self, prompt, supplied_image_tool):
        captured["prompt"] = prompt
        captured["image_tool"] = supplied_image_tool
        return "A"

    monkeypatch.setattr(
        QueryAgent,
        "_invoke_tool_agent",
        fake_invoke_tool_agent,
        raising=False,
    )

    result = agent.answer(
        title="以下哪项正确？",
        question_type="single",
        option_image_refs={"A": ["https://img.test/a.png"]},
        image_tool=image_tool,
    )

    assert result == "A"
    assert captured["image_tool"] is image_tool
    assert captured["prompt"].startswith("query-prompt")


def test_build_tool_prompt_appends_compact_option_image_context():
    agent = QueryAgent()

    prompt = agent._build_tool_prompt(
        "query-prompt",
        {
            "A": ["https://img.test/a1.png", "https://img.test/a2.png"],
            "C": ["https://img.test/c1.png"],
        },
    )

    assert prompt.startswith("query-prompt")
    assert "Option image resources:" in prompt
    assert "- A: https://img.test/a1.png, https://img.test/a2.png" in prompt
    assert "- C: https://img.test/c1.png" in prompt


def test_invalid_tool_output_reuses_correction_flow(monkeypatch):
    agent = QueryAgent()
    calls = []

    monkeypatch.setattr(query_module, "build_query_prompt", lambda *args: "query-prompt")
    monkeypatch.setattr(
        query_module,
        "build_correction_prompt",
        lambda question_type, previous_output: f"correct:{question_type}:{previous_output}",
    )
    monkeypatch.setattr(
        QueryAgent,
        "_invoke_tool_agent",
        lambda self, prompt, image_tool: "答案是 A",
        raising=False,
    )
    _set_completion(monkeypatch, lambda prompt: calls.append(prompt) or "A")

    result = agent.answer(
        title="以下哪项正确？",
        question_type="single",
        option_image_refs={"A": ["https://img.test/a.png"]},
        image_tool=object(),
    )

    assert result == "A"
    assert calls == ["correct:single:答案是 A"]


def test_batch_answer_delegates_with_title_and_returns_strings(monkeypatch):
    agent = QueryAgent()
    calls = []

    def fake_answer(**kwargs):
        calls.append(kwargs)
        return f"ans:{kwargs['title']}"

    monkeypatch.setattr(agent, "answer", fake_answer)

    results = agent.batch_answer(
        [
            {"question": "Q1", "options": ["A. 甲"], "type": "single"},
            {"question": "Q2"},
        ]
    )

    assert results == ["ans:Q1", "ans:Q2"]
    assert all(isinstance(result, str) for result in results)
    assert [call["title"] for call in calls] == ["Q1", "Q2"]
    assert all("question" not in call for call in calls)
    assert calls[0]["options"] == ["A. 甲"]
    assert calls[0]["question_type"] == "single"
    assert calls[1]["question_type"] == "unknown"
