from typing import List, Optional
from llm import completion


class AIResponder:
    """AI响应服务 - 负责使用 LLM 生成答案"""

    def __init__(self):
        """初始化 AI响应服务"""
        pass

    def generate_answer(
        self, question: str, options: List[str] = None, question_type: str = "unknown"
    ) -> str:
        """
        使用 LLM 生成答案

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型 (single, multiple, judgement, completion, unknown)

        Returns:
            AI 生成的答案字符串
        """
        prompt = self._build_query_prompt(question, options, question_type)
        response = completion.invoke(prompt)
        return response.strip()

    def _build_query_prompt(
        self, question: str, options: List[str] = None, question_type: str = "unknown"
    ) -> str:
        """
        构建查询提示词

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型

        Returns:
            提示词字符串
        """
        prompt_parts = ["请回答以下问题：\n"]
        prompt_parts.append(f"题目：{question}\n")

        if options:
            prompt_parts.append("\n选项：\n")
            for i, opt in enumerate(options):
                prompt_parts.append(f"{chr(65 + i)}. {opt}\n")

        if question_type != "unknown":
            type_map = {
                "single": "单选题",
                "multiple": "多选题",
                "judgement": "判断题",
                "completion": "填空题",
                "unknown": "未知题型",
            }
            prompt_parts.append(f"\n题型：{type_map.get(question_type, '未知题型')}\n")

        prompt_parts.append("\n请直接给出答案，不需要解释。")

        return "".join(prompt_parts)


# 单例模式 - 全局 AI响应服务
ai_responder = AIResponder()
