"""
AI服务 - 基于 LangChain/LangGraph 统一组织和协调多个 AI Agent
整合原 ai_responder 的所有功能
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from langchain.tools import tool

from agents.classification import classifier
from agents.query import query_agent
from agents.rag_chat import rag_chat
from agents.reviewer import reviewer
from utils.option_images import build_enhanced_option_text, preprocess_options
from utils.llm import analyze_images, vision_enabled

logger = logging.getLogger(__name__)


class AIService:
    """AI服务 - 统一调用各类 AI Agent（整合原 AIResponder 功能）"""

    def __init__(self):
        """初始化 AI服务"""
        self.query_agent = query_agent
        self.classifier = classifier
        self.reviewer = reviewer
        self.rag_chat = rag_chat

    @staticmethod
    def _extract_option_label(option_text: str, index: int) -> str:
        match = re.match(r"^\s*([A-Za-z])(?:[\s\.．、:：\)\]]|$)", option_text or "")
        if match:
            return match.group(1).upper()
        if index < 26:
            return chr(ord("A") + index)
        return str(index + 1)

    def _summarize_option_image(self, image_urls: List[str]) -> Optional[str]:
        if not image_urls or not vision_enabled():
            return None

        try:
            summary = analyze_images(
                "请简要概括该选项图片中的关键信息，仅输出对答题有帮助的中文结果。",
                image_urls,
            )
        except Exception as exc:
            logger.warning("Option image summarization failed: %s", exc)
            return None

        summary_text = str(summary).strip()
        return summary_text or None

    def _build_analyze_option_image_tool(
        self, option_image_refs: Optional[Dict[str, List[str]]]
    ):
        if not option_image_refs or not vision_enabled():
            return None

        allowed_urls = {
            url for image_urls in option_image_refs.values() for url in image_urls
        }
        if not allowed_urls:
            return None

        @tool
        def analyze_option_image(image_url: str) -> str:
            """分析当前题目选项中的单张图片并返回简洁说明。"""
            if image_url not in allowed_urls:
                return "该图片不属于当前题目选项，无法分析。"

            try:
                analysis = analyze_images(
                    "请简要概括这张选项图片中的关键信息，仅输出对答题有帮助的中文结果。",
                    [image_url],
                )
            except Exception as exc:
                logger.warning("Option image tool failed: %s", exc)
                return f"无法分析该选项图片：{exc}"

            analysis_text = str(analysis).strip()
            return analysis_text or "未能从该选项图片中提取到有效信息。"

        return analyze_option_image

    def _prepare_query_options(self, options: List[str]):
        if not options:
            return options, None, None

        summarizer = self._summarize_option_image if vision_enabled() else None
        option_payloads = preprocess_options(options, summarizer=summarizer)
        if not option_payloads:
            return options, None, None

        enhanced_options = [
            build_enhanced_option_text(payload) for payload in option_payloads
        ]
        option_image_refs = {}

        for index, payload in enumerate(option_payloads):
            image_urls = list(getattr(payload, "image_urls", []) or [])
            if not image_urls:
                continue

            option_text = getattr(payload, "normalized_text", None) or getattr(
                payload, "raw_option", ""
            )
            option_label = self._extract_option_label(option_text, index)
            option_image_refs[option_label] = image_urls

        image_tool = self._build_analyze_option_image_tool(option_image_refs or None)
        return enhanced_options, option_image_refs or None, image_tool

    def answer_question(
        self,
        question: str,
        options: List[str] = None,
        question_type: str = "unknown",
        auto_review: bool = False,
    ) -> Dict:
        """
        回答题目（可选自动复审）

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型
            auto_review: 是否自动复审答案

        Returns:
            包含答案和相关信息的字典
        """
        answer_result = self.generate_answer(question, options, question_type)

        result = {
            "answer": answer_result,
            "ai_generated": True,
            "reviewed": False,
        }

        if auto_review:
            review_result = self.reviewer.review(
                question=question,
                answer=answer_result,
                options=options,
                question_type=question_type,
            )

            result["reviewed"] = True
            result["review_result"] = review_result

            if review_result.get("corrected_answer"):
                result["answer"] = review_result["corrected_answer"]
                result["was_corrected"] = True

        return result

    def classify_and_answer(self, question: str, options: List[str] = None) -> Dict:
        """
        先分类再回答

        Args:
            question: 题目内容
            options: 选项列表

        Returns:
            包含分类结果和答案的字典
        """
        categories = self.classifier.classify(question, options)
        answer_result = self.generate_answer(question, options)

        return {
            "categories": categories,
            "answer": answer_result,
            "ai_generated": True,
        }

    def chat(self, query: str, use_history: bool = True) -> Dict:
        """
        RAG 对话式问答

        Args:
            query: 用户问题
            use_history: 是否使用对话历史

        Returns:
            包含回答和上下文的字典
        """
        return self.rag_chat.chat(query, use_history)

    def generate_answer(
        self, title: str, options: List[str] = None, question_type: str = "unknown"
    ) -> str:
        """
        使用 LLM 生成答案（原 AIResponder.generate_answer）

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型

        Returns:
            AI 生成的答案字符串
        """

        if question_type == "completion" and options and "段落格式" in options[0]:
            question_type = "essay"

        if question_type in ["judgement", "completion", "essay"]:
            options = None

        option_image_refs = None
        image_tool = None
        if options:
            options, option_image_refs, image_tool = self._prepare_query_options(options)

        return self.query_agent.answer(
            title=title,
            options=options,
            question_type=question_type,
            option_image_refs=option_image_refs,
            image_tool=image_tool,
        )

    def batch_generate_answers(self, questions: List[dict]) -> List[str]:
        """
        批量生成答案（原 AIResponder.batch_generate_answers）

        Args:
            questions: 题目列表，每个包含 question、options、type 等字段

        Returns:
            答案列表
        """
        results = []
        for q in questions:
            result = self.generate_answer(
                title=q["question"],
                options=q.get("options"),
                question_type=q.get("type", "unknown"),
            )
            results.append(result)
        return results


ai_service = AIService()
