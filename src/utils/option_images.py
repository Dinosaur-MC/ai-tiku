from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlsplit

_URL_START_PATTERN = re.compile(r"https?://", re.IGNORECASE)
_SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
_URL_SCAN_STOP_CHARS = set("()（）[]{}<>'\"【】《》〈〉「」『』，。、")
_TRAILING_URL_BOUNDARY_CHARS = ",，.。)）]】}>'\"!?！？;；"
_PUNCTUATION_WITHOUT_LEADING_SPACE = r",，.。!！?？;；:：)）\]】}"
_MARKDOWN_IMAGE_WRAPPER_RE = re.compile(r"!\[[^\]]*\]\(\s*\)")


@dataclass
class OptionImagePayload:
    raw_option: str
    normalized_text: str
    image_urls: list[str]
    image_summary: Optional[str] = None


@dataclass
class TitleImagePayload:
    """题目标题图片处理结果"""
    raw_title: str
    normalized_text: str
    image_urls: list[str]
    image_summary: Optional[str] = None


SummaryFn = Callable[[list[str]], Optional[str]]


def _scan_url_candidate(text: str, start: int) -> tuple[str, int]:
    end = start
    has_query_or_fragment = False

    while end < len(text):
        if text[end].isspace() or text[end] in _URL_SCAN_STOP_CHARS:
            break
        if text[end] in {"?", "#"}:
            has_query_or_fragment = True
        if not has_query_or_fragment and end > start and _URL_START_PATTERN.match(text, end):
            break
        end += 1

    return text[start:end], end


def _strip_trailing_url_punctuation(url: str) -> str:
    return url.rstrip(_TRAILING_URL_BOUNDARY_CHARS)


def _is_supported_image_url(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return any(path.endswith(extension) for extension in _SUPPORTED_IMAGE_EXTENSIONS)


def _iter_image_matches(text: str):
    source_text = "" if text is None else str(text)
    cursor = 0

    while True:
        match = _URL_START_PATTERN.search(source_text, cursor)
        if match is None:
            break

        start = match.start()
        candidate, candidate_end = _scan_url_candidate(source_text, start)
        normalized_url = _strip_trailing_url_punctuation(candidate)

        if normalized_url and _is_supported_image_url(normalized_url):
            end = start + len(normalized_url)
            yield start, end, normalized_url
            cursor = candidate_end
            continue

        cursor = start + 1


def _collapse_consecutive_duplicates(urls: list[str]) -> list[str]:
    collapsed: list[str] = []
    for url in urls:
        if not collapsed or collapsed[-1] != url:
            collapsed.append(url)
    return collapsed


def _clean_normalized_text(text: str) -> str:
    text = _MARKDOWN_IMAGE_WRAPPER_RE.sub("", text)
    # 移除标点符号前的空格
    text = re.sub(rf"[ \t]+([{_PUNCTUATION_WITHOUT_LEADING_SPACE}])", r"\1", text)
    # 将多个连续空格合并为一个
    text = re.sub(r"[ \t]{2,}", " ", text)
    # 移除中文标点前后的多余空格
    text = re.sub(r"\s+([，。、！？；：])", r"\1", text)
    text = re.sub(r"([，。、！？；：])\s+", r"\1", text)
    return text.strip()


def extract_image_urls(text):
    source_text = "" if text is None else str(text)
    urls = [url for _, _, url in _iter_image_matches(source_text)]
    return _collapse_consecutive_duplicates(urls)


def normalize_title(raw_title, summarizer=None):
    """处理题目标题，提取图片 URL 并生成摘要"""
    source_text = "" if raw_title is None else str(raw_title)
    parts: list[str] = []
    image_urls: list[str] = []
    last_index = 0

    for start, end, url in _iter_image_matches(source_text):
        parts.append(source_text[last_index:start])
        image_urls.append(url)
        last_index = end

    parts.append(source_text[last_index:])
    collapsed_urls = _collapse_consecutive_duplicates(image_urls)

    image_summary = None
    if summarizer is not None and collapsed_urls:
        try:
            summary = summarizer(collapsed_urls)
        except Exception:
            summary = None
        if summary is not None:
            summary = str(summary).strip() or None
        image_summary = summary

    return TitleImagePayload(
        raw_title=source_text,
        normalized_text=_clean_normalized_text("".join(parts)),
        image_urls=collapsed_urls,
        image_summary=image_summary,
    )


def normalize_option(raw_option, summarizer=None):
    source_text = "" if raw_option is None else str(raw_option)
    parts: list[str] = []
    image_urls: list[str] = []
    last_index = 0

    for start, end, url in _iter_image_matches(source_text):
        parts.append(source_text[last_index:start])
        image_urls.append(url)
        last_index = end

    parts.append(source_text[last_index:])
    collapsed_urls = _collapse_consecutive_duplicates(image_urls)

    image_summary = None
    if summarizer is not None and collapsed_urls:
        try:
            summary = summarizer(collapsed_urls)
        except Exception:
            summary = None
        if summary is not None:
            summary = str(summary).strip() or None
        image_summary = summary

    return OptionImagePayload(
        raw_option=source_text,
        normalized_text=_clean_normalized_text("".join(parts)),
        image_urls=collapsed_urls,
        image_summary=image_summary,
    )


def preprocess_options(options, summarizer=None):
    if not options:
        return []

    return [normalize_option(option, summarizer=summarizer) for option in options]


def build_enhanced_option_text(payload):
    extra_text = payload.image_summary
    if not extra_text and payload.image_urls:
        extra_text = "\n".join(payload.image_urls)

    if not extra_text:
        return payload.normalized_text
    if not payload.normalized_text:
        return extra_text
    return f"{payload.normalized_text}\n{extra_text}"


def build_enhanced_title_text(payload):
    """构建增强后的题目标题文本（包含图片摘要或 URL）"""
    extra_text = payload.image_summary
    if not extra_text and payload.image_urls:
        extra_text = "\n".join(payload.image_urls)

    if not extra_text:
        return payload.normalized_text
    if not payload.normalized_text:
        return extra_text
    return f"{payload.normalized_text}\n{extra_text}"


__all__ = [
    "OptionImagePayload",
    "TitleImagePayload",
    "extract_image_urls",
    "normalize_title",
    "normalize_option",
    "preprocess_options",
    "build_enhanced_option_text",
    "build_enhanced_title_text",
]
