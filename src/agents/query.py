"""
题目查询 Agent - 简化版（基于 LangChain + Pydantic）
负责回答题目并生成答案
"""

from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import logging
import sys

from llm import chat
from agents.prompts.query import build_query_prompt, CONFIDENCE_ANSWER_PROMPT

logger = logging.getLogger(__name__)


class ConfidenceResult(BaseModel):
    """置信度评估结果模型"""

    confidence: float = Field(description="置信度，0.0-1.0 之间的浮点数")
    reasoning: str = Field(description="简要说明答案的依据")


class QueryAgent:
    """题目查询 Agent - 基于 LangChain 的简化实现"""

    def __init__(self):
        """初始化题目查询 Agent"""
        self.query_history = []
        # 初始化 Pydantic 输出解析器
        self.confidence_parser = PydanticOutputParser(pydantic_object=ConfidenceResult)
        logger.info("QueryAgent 初始化完成，Pydantic 解析器已初始化")

    def answer(
        self,
        question: str,
        options: List[str] = None,
        question_type: str = "unknown",
        return_confidence: bool = False,
    ) -> Dict:
        """
        回答题目

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型
            return_confidence: 是否返回置信度

        Returns:
            包含答案的字典
        """
        logger.debug(
            f"收到查询请求：question='{question[:50]}...', type={question_type}, confidence={return_confidence}"
        )

        try:
            # 1. 构建提示词
            system_prompt, user_prompt = build_query_prompt(
                question, options, question_type
            )
            logger.debug(f"系统提示：{system_prompt[:80]}...")
            logger.debug(f"用户提示：{user_prompt[:100]}...")

            # 2. 调用 LLM（使用 stream 模式）
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.info(f"开始调用 LLM（流式输出）...")

            # 使用 stream 模式实时输出 LLM 响应
            answer_chunks = []
            print("\n[LLM 实时响应]: ", end="", flush=True)

            for chunk in chat.stream(messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    answer_chunks.append(content)
                    # 实时输出到控制台
                    print(content, end="", flush=True)

            # 输出换行
            print()

            # 合并所有片段
            answer = "".join(answer_chunks).strip()
            logger.info(f"LLM 流式输出完成，答案长度：{len(answer)}")

            # 3. 构建结果
            result = {"answer": answer, "ai_generated": True}

            # 4. 可选：评估置信度
            if return_confidence:
                logger.debug("开始评估置信度...")
                confidence_result = self._evaluate_confidence(question, options, answer)
                result.update(confidence_result)
                logger.info(
                    f"置信度评估完成：confidence={confidence_result.get('confidence')}"
                )

            # 5. 记录历史
            self.query_history.append(
                {
                    "question": question,
                    "options": options,
                    "type": question_type,
                    "result": result,
                }
            )
            logger.debug(f"查询已记录到历史，当前历史记录数：{len(self.query_history)}")

            return result

        except Exception as e:
            logger.error(f"查询失败：{str(e)}", exc_info=True)
            raise

    def _evaluate_confidence(
        self, question: str, options: List[str], answer: str
    ) -> Dict:
        """评估答案置信度（使用LangChain Pydantic 输出解析）"""
        try:
            # 构建置信度提示词
            options_text = (
                "\n".join([f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)])
                if options
                else ""
            )
            prompt = CONFIDENCE_ANSWER_PROMPT.format(
                question=question, options_section=options_text, answer=answer
            )

            # 添加格式指令
            format_instructions = self.confidence_parser.get_format_instructions()
            full_prompt = f"{prompt}\n\n{format_instructions}"

            messages = [
                SystemMessage(
                    content="请评估答案的置信度，严格按照指定格式返回 JSON。"
                ),
                HumanMessage(content=full_prompt),
            ]

            logger.debug(f"置信度评估提示：{prompt[:100]}...")

            # 使用 stream 模式调用 LLM 并自动解析为 Pydantic 对象
            logger.info(f"开始评估置信度（流式输出）...")
            print("[置信度评估]: ", end="", flush=True)

            response_chunks = []
            for chunk in chat.stream(messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    response_chunks.append(content)
                    # 实时输出
                    print(content, end="", flush=True)

            # 输出换行
            print()

            # 合并响应
            response_content = "".join(response_chunks)
            logger.debug(f"置信度评估原始返回：'{response_content}'")

            # 使用解析器自动解析
            confidence_result = self.confidence_parser.parse(response_content)

            logger.info(f"置信度解析成功：confidence={confidence_result.confidence}")
            return {
                "confidence": confidence_result.confidence,
                "reasoning": confidence_result.reasoning,
            }

        except Exception as e:
            logger.error(f"置信度评估失败：{str(e)}", exc_info=True)
            return {"confidence": 0.8, "reasoning": f"评估出错：{str(e)}"}

    def batch_answer(self, questions: List[Dict]) -> List[Dict]:
        """批量回答题目"""
        logger.info(f"开始批量处理 {len(questions)} 道题目")
        results = []
        for i, q in enumerate(questions, 1):
            logger.debug(f"处理第 {i}/{len(questions)} 题")
            result = self.answer(
                question=q["question"],
                options=q.get("options"),
                question_type=q.get("type", "unknown"),
            )
            results.append(result)
        logger.info(f"批量处理完成，共 {len(results)} 道题")
        return results

    def get_statistics(self) -> Dict:
        """获取查询统计信息"""
        if not self.query_history:
            return {"total_queries": 0, "with_confidence": 0, "average_confidence": 0.0}

        total = len(self.query_history)
        with_confidence = sum(
            1 for q in self.query_history if "confidence" in q["result"]
        )
        avg_confidence = sum(
            q["result"].get("confidence", 0.0)
            for q in self.query_history
            if "confidence" in q["result"]
        ) / max(with_confidence, 1)

        logger.debug(
            f"统计信息：total={total}, with_confidence={with_confidence}, avg={avg_confidence:.2f}"
        )
        return {
            "total_queries": total,
            "with_confidence": with_confidence,
            "average_confidence": avg_confidence,
        }

    def clear_history(self):
        """清空查询历史"""
        count = len(self.query_history)
        self.query_history = []
        logger.info(f"已清空查询历史，共清除 {count} 条记录")


# 单例模式
query_agent = QueryAgent()
logger.info("QueryAgent 单例已创建")
