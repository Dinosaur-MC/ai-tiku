"""
题目查询提示词模板 - 优化版
用于指导 LLM 准确回答题目或生成答案
"""

QUERY_SYSTEM_PROMPT = """你是一个专业的题库答题助手。请根据题目要求，给出准确、简洁的答案。

**答题规范**：
- 选择题：只输出选项字母（如：A 或 AB）
- 判断题：只输出`正确`或`错误`
- 填空题：直接顺序输出对应填空内容，多个填空之间用英文逗号分隔
- 简答题：输出核心要点，要求以完整段落格式编写

**提示**：
- 无法解析的问题，请直接返回`undefined`。

**要求**：直接输出答案，不要任何解释或多余内容。"""

QUERY_USER_PROMPT_TEMPLATE = """题目：{type_section} {question}
{options_section}
答案："""


def build_query_prompt(
    question: str, options: list = None, question_type: str = "unknown"
) -> tuple[str, str]:
    """
    构建完整的查询提示词

    Args:
        question: 题目内容
        options: 选项列表（可选）
        question_type: 题目类型

    Returns:
        (system_prompt, user_prompt) 元组
    """
    # 构建题型部分
    type_section = ""
    if question_type and question_type != "unknown":
        type_map = {
            "single": "【单选题】",
            "multiple": "【多选题】",
            "judgement": "【判断题】",
            "completion": "【填空题】",
            "essay": "【简答题】",
            "analysis": "【分析题】",
        }
        type_section = type_map.get(question_type, "")
        if type_section:
            type_section += "\n"

    if question_type == "single" or question_type == "multiple":
        # 构建选项部分
        options_section = ""
        if options:
            options_lines = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)]
            options_section = "\n".join(options_lines)

        # 构建用户提示
        user_prompt = QUERY_USER_PROMPT_TEMPLATE.format(
            type_section=type_section,
            question=question,
            options_section=options_section,
        )
    else:
        # 构建用户提示
        user_prompt = QUERY_USER_PROMPT_TEMPLATE.format(
            type_section=type_section,
            question=question,
            options_section="",
        )

    return QUERY_SYSTEM_PROMPT, user_prompt


# AI 生成答案提示词
AI_GENERATE_PROMPT = """基于以下题目信息，生成一个准确的答案。

题目：{question}

{options_section}

参考答案：{reference_answer}

请确保生成的答案：
1. 准确无误
2. 简洁明了
3. 符合题型要求
4. 与参考答案保持一致（如有）

直接输出答案即可。"""


# 多轮对话查询提示词
CONVERSATIONAL_QUERY_PROMPT = """结合对话历史和相关资料，回答用户的问题。

对话历史：
{history}

相关资料：
{context}

用户问题：{question}

请基于以上信息，给出准确、完整的回答。如果资料中没有相关信息，请如实告知。"""


# 带置信度的答案生成提示词（简化版）
CONFIDENCE_ANSWER_PROMPT = """题目：{question}
{options_section}
答案：{answer}

请用 JSON 格式返回：
{{"confidence": 0.85, "reasoning": "一句话理由"}}
"""
