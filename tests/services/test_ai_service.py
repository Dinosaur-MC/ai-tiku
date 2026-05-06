import importlib
import sys
import types
from types import SimpleNamespace

import pytest


class _Payload(SimpleNamespace):
    pass


def _payload(raw_option, normalized_text, image_urls, image_summary=None):
    return _Payload(
        raw_option=raw_option,
        normalized_text=normalized_text,
        image_urls=image_urls,
        image_summary=image_summary,
    )


def _load_ai_service_module(monkeypatch):
    fake_option_images = types.ModuleType("utils.option_images")
    fake_option_images.preprocess_options = lambda options, summarizer=None: []
    fake_option_images.build_enhanced_option_text = (
        lambda payload: payload.normalized_text
    )
    monkeypatch.setitem(sys.modules, "utils.option_images", fake_option_images)

    import utils.llm as llm

    monkeypatch.setattr(llm, "vision_enabled", lambda: False, raising=False)
    monkeypatch.setattr(
        llm,
        "analyze_images",
        lambda prompt, image_urls, **kwargs: "vision-output",
        raising=False,
    )

    sys.modules.pop("services.ai_service", None)
    return importlib.import_module("services.ai_service")


def test_generate_answer_preprocesses_image_backed_choice_options(monkeypatch):
    ai_service_module = _load_ai_service_module(monkeypatch)
    service = ai_service_module.AIService()
    captured = {}

    option_payloads = [
        _payload(
            "A. 甲 https://img.test/a.png",
            "A. 甲",
            ["https://img.test/a.png"],
            "图示甲",
        ),
        _payload("B. 乙", "B. 乙", []),
    ]

    def fake_preprocess(options, summarizer=None):
        assert options == ["A. 甲 https://img.test/a.png", "B. 乙"]
        assert callable(summarizer)
        return option_payloads

    monkeypatch.setattr(ai_service_module, "preprocess_options", fake_preprocess)
    monkeypatch.setattr(
        ai_service_module,
        "build_enhanced_option_text",
        lambda payload: (
            f"{payload.normalized_text}\n{payload.image_summary}"
            if payload.image_summary
            else payload.normalized_text
        ),
    )
    monkeypatch.setattr(ai_service_module, "vision_enabled", lambda: True)
    monkeypatch.setattr(
        ai_service_module,
        "analyze_images",
        lambda prompt, image_urls, **kwargs: "unused-in-this-test",
    )
    service.query_agent = SimpleNamespace(
        answer=lambda **kwargs: captured.update(kwargs) or "A"
    )

    result = service.generate_answer(
        title="以下哪项正确？",
        options=["A. 甲 https://img.test/a.png", "B. 乙"],
        question_type="single",
    )

    assert result == "A"
    assert captured["title"] == "以下哪项正确？"
    assert captured["question_type"] == "single"
    assert captured["options"] == ["A. 甲\n图示甲", "B. 乙"]


def test_generate_answer_passes_image_tool_and_option_refs_when_vision_enabled(
    monkeypatch,
):
    ai_service_module = _load_ai_service_module(monkeypatch)
    service = ai_service_module.AIService()
    captured = {}
    analysis_calls = []

    monkeypatch.setattr(
        ai_service_module,
        "preprocess_options",
        lambda options, summarizer=None: [
            _payload(
                "A. 图一 https://img.test/a1.png https://img.test/a2.png",
                "A. 图一",
                ["https://img.test/a1.png", "https://img.test/a2.png"],
                "图一摘要",
            ),
            _payload(
                "B. 图二 https://img.test/b1.png",
                "B. 图二",
                ["https://img.test/b1.png"],
                "图二摘要",
            ),
        ],
    )
    monkeypatch.setattr(
        ai_service_module,
        "build_enhanced_option_text",
        lambda payload: f"{payload.normalized_text}\n{payload.image_summary}",
    )
    monkeypatch.setattr(ai_service_module, "vision_enabled", lambda: True)

    def fake_analyze_images(prompt, image_urls, **kwargs):
        analysis_calls.append((prompt, image_urls, kwargs))
        return "选项图片说明"

    monkeypatch.setattr(ai_service_module, "analyze_images", fake_analyze_images)
    service.query_agent = SimpleNamespace(
        answer=lambda **kwargs: captured.update(kwargs) or "B"
    )

    result = service.generate_answer(
        title="看图选择正确答案",
        options=[
            "A. 图一 https://img.test/a1.png https://img.test/a2.png",
            "B. 图二 https://img.test/b1.png",
        ],
        question_type="single",
    )

    assert result == "B"
    assert captured["title"] == "看图选择正确答案"
    assert captured["option_image_refs"] == {
        "A": ["https://img.test/a1.png", "https://img.test/a2.png"],
        "B": ["https://img.test/b1.png"],
    }
    assert captured["image_tool"] is not None
    assert captured["options"] == ["A. 图一\n图一摘要", "B. 图二\n图二摘要"]

    assert (
        captured["image_tool"].invoke({"image_url": "https://img.test/a1.png"})
        == "选项图片说明"
    )
    assert analysis_calls[0][1] == ["https://img.test/a1.png"]
    assert "选项图片" in analysis_calls[0][0]

    invalid_result = captured["image_tool"].invoke(
        {"image_url": "https://img.test/other.png"}
    )
    assert "不属于当前题目选项" in invalid_result


def test_generate_answer_keeps_raw_image_urls_when_vision_disabled(monkeypatch):
    ai_service_module = _load_ai_service_module(monkeypatch)
    service = ai_service_module.AIService()
    captured = {}

    def fake_preprocess(options, summarizer=None):
        assert summarizer is None
        return [
            _payload(
                "A. 甲 https://img.test/a.png",
                "A. 甲",
                ["https://img.test/a.png"],
                None,
            )
        ]

    monkeypatch.setattr(ai_service_module, "preprocess_options", fake_preprocess)
    monkeypatch.setattr(
        ai_service_module,
        "build_enhanced_option_text",
        lambda payload: f"{payload.normalized_text}\n{payload.image_urls[0]}",
    )
    monkeypatch.setattr(ai_service_module, "vision_enabled", lambda: False)
    service.query_agent = SimpleNamespace(
        answer=lambda **kwargs: captured.update(kwargs) or "A"
    )

    result = service.generate_answer(
        title="看图选择正确答案",
        options=["A. 甲 https://img.test/a.png"],
        question_type="single",
    )

    assert result == "A"
    assert captured["title"] == "看图选择正确答案"
    assert captured["options"] == ["A. 甲\nhttps://img.test/a.png"]
    assert captured["option_image_refs"] == {"A": ["https://img.test/a.png"]}
    assert captured["image_tool"] is None


def test_generate_answer_continues_when_image_summarization_fails(monkeypatch):
    ai_service_module = _load_ai_service_module(monkeypatch)
    service = ai_service_module.AIService()
    captured = {}

    def fake_preprocess(options, summarizer=None):
        assert callable(summarizer)
        summary = summarizer(["https://img.test/a.png"])
        return [
            _payload(
                "A. 甲 https://img.test/a.png",
                "A. 甲",
                ["https://img.test/a.png"],
                summary,
            )
        ]

    monkeypatch.setattr(ai_service_module, "preprocess_options", fake_preprocess)
    monkeypatch.setattr(
        ai_service_module,
        "build_enhanced_option_text",
        lambda payload: (
            f"{payload.normalized_text}\n{payload.image_summary}"
            if payload.image_summary
            else f"{payload.normalized_text}\n{payload.image_urls[0]}"
        ),
    )
    monkeypatch.setattr(ai_service_module, "vision_enabled", lambda: True)
    monkeypatch.setattr(
        ai_service_module,
        "analyze_images",
        lambda prompt, image_urls, **kwargs: (_ for _ in ()).throw(
            RuntimeError("vision backend unavailable")
        ),
    )
    service.query_agent = SimpleNamespace(
        answer=lambda **kwargs: captured.update(kwargs) or "A"
    )

    result = service.generate_answer(
        title="看图选择正确答案",
        options=["A. 甲 https://img.test/a.png"],
        question_type="single",
    )

    assert result == "A"
    assert captured["title"] == "看图选择正确答案"
    assert captured["options"] == ["A. 甲\nhttps://img.test/a.png"]
    assert captured["option_image_refs"] == {"A": ["https://img.test/a.png"]}


@pytest.mark.parametrize(
    ("question_type", "options", "expected_question_type"),
    [
        ("judgement", ["A. 对 https://img.test/a.png"], "judgement"),
        ("completion", ["段落格式 https://img.test/a.png"], "essay"),
    ],
)
def test_generate_answer_bypasses_preprocessing_for_non_choice_types(
    monkeypatch, question_type, options, expected_question_type
):
    ai_service_module = _load_ai_service_module(monkeypatch)
    service = ai_service_module.AIService()
    captured = {}
    preprocess_calls = []

    monkeypatch.setattr(
        ai_service_module,
        "preprocess_options",
        lambda options, summarizer=None: preprocess_calls.append((options, summarizer)),
    )
    service.query_agent = SimpleNamespace(
        answer=lambda **kwargs: captured.update(kwargs) or "答案"
    )

    result = service.generate_answer(
        title="非选择题",
        options=options,
        question_type=question_type,
    )

    assert result == "答案"
    assert preprocess_calls == []
    assert captured["title"] == "非选择题"
    assert captured["question_type"] == expected_question_type
    assert captured["options"] is None
    assert captured["option_image_refs"] is None
    assert captured["image_tool"] is None
