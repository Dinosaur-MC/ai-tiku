import pytest

from utils.option_images import (
    OptionImagePayload,
    build_enhanced_option_text,
    extract_image_urls,
    normalize_option,
    preprocess_options,
)


def test_extract_image_urls_returns_single_image_url():
    text = "A. 查看图片 https://cdn.example.com/a.png"

    assert extract_image_urls(text) == ["https://cdn.example.com/a.png"]


def test_extract_image_urls_collapses_back_to_back_duplicate_urls():
    text = "https://cdn.example.com/a.pnghttps://cdn.example.com/a.png"

    assert extract_image_urls(text) == ["https://cdn.example.com/a.png"]


def test_extract_image_urls_splits_adjacent_distinct_urls():
    text = "https://cdn.example.com/a.pnghttps://cdn.example.com/b.png"

    assert extract_image_urls(text) == [
        "https://cdn.example.com/a.png",
        "https://cdn.example.com/b.png",
    ]


def test_extract_image_urls_splits_adjacent_distinct_urls_with_mixed_case_scheme():
    text = "https://cdn.example.com/a.pngHTTPS://cdn.example.com/b.png"

    assert extract_image_urls(text) == [
        "https://cdn.example.com/a.png",
        "HTTPS://cdn.example.com/b.png",
    ]


def test_extract_image_urls_preserves_nested_url_inside_query_string():
    text = "https://cdn.example.com/a.png?next=https://other.example.com/x"

    assert extract_image_urls(text) == [
        "https://cdn.example.com/a.png?next=https://other.example.com/x"
    ]


def test_extract_image_urls_does_not_double_count_nested_inner_image_url():
    text = "https://cdn.example.com/a.png?next=https://other.example.com/b.png"

    assert extract_image_urls(text) == [
        "https://cdn.example.com/a.png?next=https://other.example.com/b.png"
    ]


def test_extract_image_urls_keeps_inner_image_when_outer_url_is_not_image():
    text = "https://proxy.example.com/fetch?src=https://other.example.com/b.png"

    assert extract_image_urls(text) == ["https://other.example.com/b.png"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://cdn.example.com/a.png?x=1.2", "https://cdn.example.com/a.png?x=1.2"),
        ("https://cdn.example.com/a.png?ids=1,2", "https://cdn.example.com/a.png?ids=1,2"),
        ("https://cdn.example.com/a.png#frag.part", "https://cdn.example.com/a.png#frag.part"),
        ("https://cdn.example.com/a.png.webp", "https://cdn.example.com/a.png.webp"),
    ],
)
def test_extract_image_urls_preserves_internal_query_fragment_and_multi_extension_text(
    text, expected
):
    assert extract_image_urls(text) == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://cdn.example.com/a.png,", "https://cdn.example.com/a.png"),
        ("https://cdn.example.com/a.png)", "https://cdn.example.com/a.png"),
        ("https://cdn.example.com/a.png?size=1,", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?size=1，", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png#frag,", "https://cdn.example.com/a.png#frag"),
        ("https://cdn.example.com/a.png#frag，", "https://cdn.example.com/a.png#frag"),
        ("https://cdn.example.com/a.png?size=1)", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?size=1）", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?size=1.", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?x=1.2.", "https://cdn.example.com/a.png?x=1.2"),
        ("https://cdn.example.com/a.png?size=1...", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?size=1.)", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png?size=1。）", "https://cdn.example.com/a.png?size=1"),
        ("https://cdn.example.com/a.png#frag.", "https://cdn.example.com/a.png#frag"),
    ],
)
def test_extract_image_urls_strips_supported_trailing_punctuation(text, expected):
    assert extract_image_urls(text) == [expected]


def test_normalize_option_preserves_surrounding_punctuation_after_url_removal():
    payload = normalize_option(
        "A. 见图（https://cdn.example.com/a.png?size=1）后作答, 并说明原因。"
    )

    assert isinstance(payload, OptionImagePayload)
    assert payload.normalized_text == "A. 见图（）后作答, 并说明原因。"
    assert payload.image_urls == ["https://cdn.example.com/a.png?size=1"]


def test_normalize_option_treats_outer_image_with_nested_inner_image_as_single_match():
    payload = normalize_option(
        "A. 见图 https://cdn.example.com/a.png?next=https://other.example.com/b.png, 结束"
    )

    assert payload.normalized_text == "A. 见图, 结束"
    assert payload.image_urls == [
        "https://cdn.example.com/a.png?next=https://other.example.com/b.png"
    ]


def test_normalize_option_removes_markdown_image_wrapper_noise():
    payload = normalize_option("A. ![img](https://img.test/a.png)")

    assert payload.normalized_text == "A."
    assert payload.image_urls == ["https://img.test/a.png"]
    assert build_enhanced_option_text(payload) == "A.\nhttps://img.test/a.png"


def test_normalize_option_removes_space_before_following_punctuation():
    payload = normalize_option("A. 先看 https://cdn.example.com/a.png, 再作答")

    assert payload.normalized_text == "A. 先看, 再作答"
    assert payload.image_urls == ["https://cdn.example.com/a.png"]


def test_normalize_option_uses_successful_summarizer_result():
    def summarizer(urls):
        assert urls == ["https://cdn.example.com/a.png"]
        return "图片显示一个红色三角形"

    payload = normalize_option("B. 请观察 https://cdn.example.com/a.png", summarizer=summarizer)

    assert payload.image_summary == "图片显示一个红色三角形"
    assert build_enhanced_option_text(payload) == "B. 请观察\n图片显示一个红色三角形"


def test_normalize_option_falls_back_when_summarizer_raises():
    def summarizer(_urls):
        raise RuntimeError("boom")

    payload = normalize_option("C. 参考 https://cdn.example.com/a.png", summarizer=summarizer)

    assert payload.image_summary is None
    assert build_enhanced_option_text(payload) == "C. 参考\nhttps://cdn.example.com/a.png"


def test_preprocess_options_returns_payloads_in_input_order():
    options = [
        "A. 第一项 https://cdn.example.com/1.png",
        "B. 纯文本选项",
        "C. 第二项 https://cdn.example.com/2.png",
    ]

    def summarizer(urls):
        return f"summary:{urls[0].rsplit('/', 1)[-1]}" if urls else None

    payloads = preprocess_options(options, summarizer=summarizer)

    assert all(isinstance(payload, OptionImagePayload) for payload in payloads)
    assert [payload.raw_option for payload in payloads] == options
    assert [payload.normalized_text for payload in payloads] == [
        "A. 第一项",
        "B. 纯文本选项",
        "C. 第二项",
    ]
    assert [payload.image_urls for payload in payloads] == [
        ["https://cdn.example.com/1.png"],
        [],
        ["https://cdn.example.com/2.png"],
    ]
    assert [payload.image_summary for payload in payloads] == [
        "summary:1.png",
        None,
        "summary:2.png",
    ]
