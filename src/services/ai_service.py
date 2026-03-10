"""
AI服务 - 基于 LangChain/LangGraph 统一组织和协调多个 AI Agent
整合原 ai_responder 的所有功能
"""

from typing import List, Dict, Optional
from agents.query import query_agent
from agents.classification import classifier
from agents.reviewer import reviewer
from agents.rag_chat import rag_chat


class AIService:
    """AI服务 - 统一调用各类 AI Agent（整合原 AIResponder 功能）"""

    def __init__(self):
        """初始化 AI服务"""
        self.query_agent = query_agent
        self.classifier = classifier
        self.reviewer = reviewer
        self.rag_chat = rag_chat

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
        # 1. 生成答案
        answer_result = self.query_agent.answer(
            question=question, options=options, question_type=question_type
        )

        result = {
            "answer": answer_result["answer"],
            "ai_generated": True,
            "reviewed": False,
        }

        # 2. 如果需要，自动复审
        if auto_review:
            review_result = self.reviewer.review(
                question=question,
                answer=answer_result["answer"],
                options=options,
                question_type=question_type,
            )

            result["reviewed"] = True
            result["review_result"] = review_result

            # 如果复审认为需要修正，使用修正后的答案
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
        # 1. 分类
        categories = classifier.classify(question, options)

        # 2. 回答
        answer_result = self.query_agent.answer(question=question, options=options)

        return {
            "categories": categories,
            "answer": answer_result["answer"],
            "ai_generated": True,
        }

    def full_process(
        self, question: str, options: List[str] = None, question_type: str = "unknown"
    ) -> Dict:
        """
        完整流程：分类 -> 回答 -> 复审

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型

        Returns:
            包含所有处理结果的字典
        """
        # 1. 分类
        categories = classifier.classify(question, options)

        # 2. 回答
        answer_result = self.query_agent.answer(
            question=question, options=options, question_type=question_type
        )

        # 3. 复审
        review_result = self.reviewer.review(
            question=question,
            answer=answer_result["answer"],
            options=options,
            question_type=question_type,
        )

        # 4. 整合结果
        final_answer = review_result.get("corrected_answer") or answer_result["answer"]

        return {
            "categories": categories,
            "original_answer": answer_result["answer"],
            "final_answer": final_answer,
            "review_result": review_result,
            "was_corrected": review_result.get("corrected_answer") is not None,
            "statistics": {
                "query_stats": self.query_agent.get_statistics(),
                "review_stats": self.reviewer.get_review_statistics(),
            },
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

    def batch_process(self, questions: List[Dict]) -> List[Dict]:
        """
        批量处理题目

        Args:
            questions: 题目列表，每个包含 question、options、type 等字段

        Returns:
            处理结果列表
        """
        results = []
        for q in questions:
            result = self.full_process(
                question=q["question"],
                options=q.get("options"),
                question_type=q.get("type", "unknown"),
            )
            results.append(result)
        return results

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

        result = self.query_agent.answer(
            title=title, options=options, question_type=question_type
        )
        return result

    def batch_generate_answers(self, questions: List[dict]) -> List[dict]:
        """
        批量生成答案（原 AIResponder.batch_generate_answers）

        Args:
            questions: 题目列表，每个包含 question、options、type 等字段

        Returns:
            答案列表
        """
        results = []
        for q in questions:
            result = self.query_agent.answer(
                question=q["question"],
                options=q.get("options"),
                question_type=q.get("type", "unknown"),
            )
            results.append(result)
        return results


# 单例模式
ai_service = AIService()
