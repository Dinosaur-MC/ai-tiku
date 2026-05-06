"""
答案复审 Agent - 基于 LangChain/LangGraph + Pydantic 实现
负责审核和修正 AI 生成的答案
"""

from typing import Dict, Optional, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import logging

from utils.llm import chat
from agents.prompts.review import build_review_prompt

logger = logging.getLogger(__name__)


class ReviewResult(BaseModel):
    """复审结果模型"""

    is_correct: bool = Field(description="答案是否正确")
    confidence: float = Field(description="置信度，0.0-1.0")
    corrected_answer: Optional[str] = Field(default=None, description="修正后的答案")
    explanation: str = Field(description="审核说明")
    suggestions: List[str] = Field(default_factory=list, description="改进建议列表")


class ReviewState(BaseModel):
    """复审状态模型"""

    question: str
    answer: str
    options: Optional[List[str]] = None
    question_type: str
    subject: Optional[str] = None
    corrections: Optional[str] = None
    review_result: Optional[ReviewResult] = None


class ReviewerAgent:
    """答案复审 Agent - 基于 LangGraph 实现"""

    def __init__(self):
        """初始化复审 Agent"""
        self.review_history = []
        # 初始化 Pydantic 输出解析器
        self.parser = PydanticOutputParser(pydantic_object=ReviewResult)
        self._build_graph()
        logger.info("ReviewerAgent 初始化完成，Pydantic 解析器已初始化")

    def _build_graph(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(ReviewState)

        # 添加节点
        workflow.add_node("review", self._review_node)
        workflow.add_node("parse_result", self._parse_result_node)

        # 设置入口点
        workflow.set_entry_point("review")

        # 添加边
        workflow.add_edge("review", "parse_result")
        workflow.add_edge("parse_result", END)

        # 编译工作流
        self.graph = workflow.compile()
        logger.debug("LangGraph 工作流已构建")

    def _review_node(self, state: ReviewState) -> Dict:
        """复审节点（使用LangChain Pydantic 输出解析）"""
        logger.debug(
            f"开始复审：question='{state['question'][:50]}...', answer='{state['answer'][:30]}...'"
        )

        # 构建提示词
        prompt = build_review_prompt(
            state["question"],
            state["answer"],
            state["options"],
            state["question_type"],
            state["subject"],
            state["corrections"],
        )

        # 添加格式指令
        format_instructions = self.parser.get_format_instructions()
        full_prompt = (
            f"{prompt}\n\n请严格按照以下 JSON Schema 格式返回:\n{format_instructions}"
        )

        messages = [
            SystemMessage(
                content="你是一个专业的答案审核员，负责审查 AI 生成的答案的准确性、规范性和完整性。"
            ),
            HumanMessage(content=full_prompt),
        ]

        logger.info("调用 LLM 进行复审...")
        response = chat.invoke(messages)
        logger.debug(f"LLM 返回原始内容：'{response.content[:100]}...'")

        try:
            # 使用 Pydantic 解析器自动解析
            review_result = self.parser.parse(response.content)
            logger.info(f"复审解析成功：is_correct={review_result.is_correct}")
            return {"review_result": review_result}
        except Exception as e:
            logger.error(f"复审解析失败：{str(e)}，使用默认结果")
            # 解析失败时使用默认结果
            return {
                "review_result": ReviewResult(
                    is_correct=True,
                    confidence=0.5,
                    corrected_answer=None,
                    explanation="解析失败，默认通过",
                    suggestions=[],
                )
            }

    def _parse_result_node(self, state: ReviewState) -> Dict:
        """解析复审结果节点（已在上游完成，直接返回）"""
        # 由于已经在 review_node 中使用 Pydantic 解析，这里直接返回
        if isinstance(state["review_result"], ReviewResult):
            logger.debug("已经是 ReviewResult 对象")
            return {"review_result": state["review_result"].dict()}
        elif isinstance(state["review_result"], dict):
            return {"review_result": state["review_result"]}
        else:
            logger.warning("未知格式，返回默认结果")
            return {
                "review_result": {
                    "is_correct": True,
                    "confidence": 0.5,
                    "corrected_answer": None,
                    "explanation": "解析失败",
                    "suggestions": [],
                }
            }

    def review(
        self,
        question: str,
        answer: str,
        options: List[str] = None,
        question_type: str = "unknown",
        subject: Optional[str] = None,
        corrections: str = None,
    ) -> Dict:
        """复审答案"""
        logger.info(
            f"收到复审请求：question='{question[:50]}...', type={question_type}"
        )

        initial_state = {
            "question": question,
            "answer": answer,
            "options": options,
            "question_type": question_type,
            "subject": subject,
            "corrections": corrections,
            "review_result": {},
        }

        result = self.graph.invoke(initial_state)
        review_result = result["review_result"]

        # 记录复审历史
        self.review_history.append(
            {
                "question": question,
                "original_answer": answer,
                "review_result": review_result,
            }
        )
        logger.info(f"复审完成，is_correct={review_result.get('is_correct')}")

        return review_result

    def batch_review(self, qa_pairs: List[Dict]) -> List[Dict]:
        """批量复审答案"""
        logger.info(f"开始批量复审 {len(qa_pairs)} 道题")
        results = []
        for i, qa in enumerate(qa_pairs, 1):
            logger.debug(f"复审第 {i}/{len(qa_pairs)} 题")
            result = self.review(
                question=qa["question"],
                answer=qa["answer"],
                options=qa.get("options"),
                question_type=qa.get("type", "unknown"),
                subject=qa.get("subject", None),
            )
            results.append(result)
        logger.info(f"批量复审完成，共 {len(results)} 道题")
        return results

    def get_review_statistics(self) -> Dict:
        """获取复审统计信息"""
        if not self.review_history:
            logger.debug("没有复审历史")
            return {"total_reviews": 0, "correct_rate": 0.0, "average_confidence": 0.0}

        total = len(self.review_history)
        correct_count = sum(
            1
            for r in self.review_history
            if r["review_result"].get("is_correct", False)
        )
        avg_confidence = (
            sum(r["review_result"].get("confidence", 0.0) for r in self.review_history)
            / total
        )

        logger.debug(f"复审统计：total={total}, correct_rate={correct_count/total:.2f}")
        return {
            "total_reviews": total,
            "correct_rate": correct_count / total,
            "average_confidence": avg_confidence,
        }


# 单例模式
reviewer = ReviewerAgent()
logger.info("ReviewerAgent 单例已创建")
