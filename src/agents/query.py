"""
题目查询 Agent - 简化版（基于 LangChain ）
负责回答题目并生成答案
"""

from typing import Dict, List, Optional
import logging
import re

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agents.prompts.query import (
    QUERY_OUTPUT_CHECK_REGEX,
    build_correction_prompt,
    build_query_prompt,
    build_type_detection_prompt,
)
from utils.llm import chat, completion
from utils.string_tool import common_prefix

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
        option_image_refs: Optional[Dict[str, List[str]]] = None,
        image_tool=None,
    ) -> str:
        """
        回答题目

        Args:
            title: 题目内容
            options: 选项列表
            question_type: 题目类型
            subject: 科目/课程名称
            option_image_refs: 选项对应的图片资源引用
            image_tool: 图片分析工具

        Returns:
            答案
        """

        logger.info(
            f"收到查询请求：subject='{subject}', question='{title[:50]}...', type={question_type}"
        )
        formatted_options = self._format_options(options)

        try:
            if question_type == "unknown" or not QUERY_OUTPUT_CHECK_REGEX.get(
                question_type
            ):
                logger.debug("Detecting Question Type...")
                detect_prompt = build_type_detection_prompt(title, formatted_options)
                question_type = completion.invoke(detect_prompt)
                question_type = question_type.strip().lower()

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
                    question_type = "essay"

                logger.debug(f"Detected Type: {question_type}")

            logger.debug("Generating Answer...")
            query_prompt = build_query_prompt(
                question_type, title, formatted_options, subject
            )
            if self._should_use_image_tool(image_tool, option_image_refs):
                tool_prompt = self._build_tool_prompt(query_prompt, option_image_refs)
                answer = self._invoke_tool_agent(tool_prompt, image_tool).strip()
            else:
                answer = completion.invoke(query_prompt).strip()

            answer = re.sub(r"^<think>(.*?)</think>", "", answer, flags=re.DOTALL).strip()
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

            logger.debug("Checking Format...")
            is_valid = (
                self._check_output_format(answer, question_type) or answer == "None"
            )

            if not is_valid:
                logger.debug(
                    f"Format Check Failed for type '{question_type}'. Triggering Correction..."
                )
                correction_prompt = build_correction_prompt(question_type, answer)
                corrected_answer = completion.invoke(correction_prompt).strip()
                logger.debug(f"Corrected Answer: {corrected_answer}")

                if not self._check_output_format(corrected_answer, question_type):
                    logger.warning(
                        "Correction failed format check. Returning raw corrected output."
                    )
                logger.info(
                    f"查询结果（{len(corrected_answer)}）：{corrected_answer[:50]}..."
                )
                return corrected_answer

            logger.info(f"查询结果（{len(answer)}）：{answer[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"查询失败：{str(e)}", exc_info=True)
            raise

    def batch_answer(self, questions: List[Dict]) -> List[str]:
        """批量回答题目，返回答案字符串列表"""

        logger.info(f"开始批量处理 {len(questions)} 道题目")
        results: List[str] = []
        for i, q in enumerate(questions, 1):
            logger.debug(f"处理第 {i}/{len(questions)} 题")
            result = self.answer(
                title=q["question"],
                options=q.get("options"),
                question_type=q.get("type", "unknown"),
                subject=q.get("subject", None),
            )
            results.append(result)
        logger.info(f"批量处理完成，共 {len(results)} 道题")
        return results

    @staticmethod
    def _format_options(options: Optional[List[str]]) -> Optional[str]:
        """将选项列表格式化为按行分隔的文本。"""
        if not options:
            return None
        if isinstance(options, str):
            return options
        return "\n".join(options)

    @staticmethod
    def _should_use_image_tool(
        image_tool, option_image_refs: Optional[Dict[str, List[str]]]
    ) -> bool:
        """当存在图片资源且提供了图片工具时，走工具分支。"""
        if image_tool is None or not option_image_refs:
            return False
        return any(image_refs for image_refs in option_image_refs.values())

    @staticmethod
    def _build_tool_prompt(
        prompt: str, option_image_refs: Optional[Dict[str, List[str]]]
    ) -> str:
        """为工具调用补充紧凑的选项图片资源上下文。"""
        if not option_image_refs:
            return prompt

        resource_lines = ["Option image resources:"]
        for option, image_refs in option_image_refs.items():
            if not image_refs:
                continue
            resource_lines.append(f"- {option}: {', '.join(image_refs)}")

        if len(resource_lines) == 1:
            return prompt
        return f"{prompt}\n\n" + "\n".join(resource_lines)

    @staticmethod
    def _invoke_tool_agent(prompt: str, image_tool) -> str:
        """使用带工具的 chat agent 处理包含图片资源的题目。"""
        agent = create_agent(model=chat, tools=[image_tool])
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        messages = result.get("messages", [])
        if not messages:
            return ""

        content = getattr(messages[-1], "content", messages[-1])
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if text is not None:
                        text_parts.append(str(text))
                else:
                    text_parts.append(str(block))
            return "".join(text_parts).strip()

        return str(content).strip()

    @staticmethod
    def _check_output_format(answer: str, question_type: str) -> bool:
        """Enhanced format checker with semantic validation for completion type"""

        pattern = QUERY_OUTPUT_CHECK_REGEX.get(question_type)
        if not pattern:
            return False

        if not re.match(pattern, answer.strip()):
            return False

        return True


query_agent = QueryAgent()
logger.info("QueryAgent 单例已创建")
