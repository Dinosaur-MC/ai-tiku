"""
题目查询 Agent - 简化版（基于 LangChain ）
负责回答题目并生成答案
"""

from typing import List, Dict, Optional
import re
from agents.prompts.query import (
    QUERY_OUTPUT_CHECK_REGEX,
    build_type_detection_prompt,
    build_query_prompt,
    build_correction_prompt,
)
from utils.llm import completion
from utils.string_tool import common_prefix
import logging

logger = logging.getLogger(__name__)


class QueryAgent:
    """题目查询 Agent - 基于 LangChain 的简化实现"""

    def __init__(self):
        """初始化题目查询 Agent"""
        pass

    def answer(
        self,
        title: str,
        options: Optional[List[str]] = None,
        question_type: str = "unknown",
        subject: Optional[str] = None,
    ) -> Dict:
        """
        回答题目

        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型
            subject: 科目/课程名称

        Returns:
            答案
        """

        logger.info(
            f"收到查询请求：subject='{subject}', question='{(title+str(options))[:128]}...', type={question_type}"
        )

        try:
            # 1. Type Detection
            if question_type == "unknown" or not QUERY_OUTPUT_CHECK_REGEX.get(
                question_type
            ):
                logger.debug("Detecting Question Type...")
                detect_prompt = build_type_detection_prompt(title, options)
                question_type = completion.invoke(detect_prompt)
                question_type = question_type.strip().lower()

                # Map potential variations to standard types
                type_map = {
                    "single choice": "single",
                    "单选题": "single",
                    "multiple choice": "multiple",
                    "多选题": "multiple",
                    "true/false": "judgement",
                    "判断题": "judgement",
                    "fill-in-the-blank": "completion",
                    "填空题": "completion",
                    "essay": "essay",
                    "问答题": "essay",
                }
                for key, val in type_map.items():
                    if key in question_type:
                        question_type = val
                        break

                if question_type not in QUERY_OUTPUT_CHECK_REGEX:
                    question_type = "essay"  # Default fallback

                logger.debug(f"Detected Type: {question_type}")

            # 2. Generate Answer
            logger.debug("Generating Answer...")
            query_prompt = build_query_prompt(question_type, title, options, subject)
            answer: str = completion.invoke(query_prompt).strip()
            answer = re.sub(r"^<think>(.*?)</think>", "", answer)
            logger.debug(f"Raw Answer: {answer}")

            if question_type == "completion":
                new_title = title.strip()
                prefix = common_prefix(answer, new_title)
                while prefix:
                    new_title = new_title.removeprefix(prefix).strip()
                    answer = answer.removeprefix(prefix).strip()
                    logger.debug(f"Removed Prefix: {prefix}")
                    prefix = common_prefix(answer, new_title)
                if answer.startswith((":", "：")):
                    answer = answer[1:].strip()

            # 3. Format Check
            logger.debug("Checking Format...")
            is_valid = (
                self._check_output_format(answer, question_type) or answer == "None"
            )

            if not is_valid:
                logger.debug(
                    f"Format Check Failed for type '{question_type}'. Triggering Correction..."
                )

                # 4. Correction Loop (Max 1 attempt)
                correction_prompt = build_correction_prompt(question_type, answer)
                corrected_answer = completion.invoke(correction_prompt).strip()
                logger.debug(f"Corrected Answer: {corrected_answer}")

                # Final Check
                if not self._check_output_format(corrected_answer, question_type):
                    logger.warning(
                        "Correction failed format check. Returning raw corrected output."
                    )
                logger.info(
                    f"查询结果（{len(corrected_answer)}）：{corrected_answer[:50]}"
                    + "..."
                    if len(corrected_answer) > 50
                    else ""
                )
                return corrected_answer
            else:
                logger.info(
                    f"查询结果（{len(answer)}）：{answer[:50]}" + "..."
                    if len(answer) > 50
                    else ""
                )
                return answer

        except Exception as e:
            logger.error(f"查询失败：{str(e)}", exc_info=True)
            raise

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

    @staticmethod
    def _check_output_format(answer: str, question_type: str) -> bool:
        """Enhanced format checker with semantic validation for completion type"""

        pattern = QUERY_OUTPUT_CHECK_REGEX.get(question_type)
        if not pattern:
            return False

        # Basic regex check
        if not re.match(pattern, answer.strip()):
            return False

        return True


# 单例模式
query_agent = QueryAgent()
logger.info("QueryAgent 单例已创建")
