"""
答案复审提示词模板
用于指导 LLM 审核和修正 AI 生成的答案
"""

REVIEW_SYSTEM_PROMPT = """你是一个专业的答案审核员。你的任务是审查 AI 生成的答案，确保其准确性、规范性和完整性。

审核维度：
1. 准确性：答案是否正确回答了问题
2. 匹配性：答案是否与给定选项匹配（如有选项）
3. 事实性：答案是否存在事实错误
4. 规范性：答案格式是否符合题型要求
5. 清晰性：答案表述是否清晰、简洁

审核标准：
- 对于选择题：答案必须是正确的选项字母
- 对于判断题：答案必须是"正确"或"错误"
- 对于填空题：答案必须是准确的填空内容
- 对于简答题：答案必须包含核心要点

输出要求：
返回 JSON 格式的审核结果，包含以下字段：
- is_correct: 是否正确（布尔值）
- confidence: 置信度（0-1 之间的浮点数）
- corrected_answer: 修正后的答案（如有必要）
- explanation: 审核说明（简明扼要）
- suggestions: 改进建议列表（可选）
"""

REVIEW_USER_PROMPT_TEMPLATE = """请审核以下题目的答案。

学科/课程: {subject}
题目：{question}

{options_section}

{type_section}

待审核的答案：{answer}

{corrections_section}

请从准确性、匹配性、事实性、规范性和清晰性等维度进行审核，返回 JSON 格式的审核结果。"""


def build_review_prompt(
    question: str,
    answer: str,
    options: list = None,
    question_type: str = "unknown",
    subject: str = None,
    corrections: str = None,
) -> str:
    """
    构建完整的复审提示词

    Args:
        question: 题目内容
        answer: 待审核的答案
        options: 选项列表（可选）
        question_type: 题目类型
        subject: 科目/课程名称
        corrections: 用户修正建议（可选）

    Returns:
        完整的提示词字符串
    """
    # 构建选项部分
    options_section = ""
    if options:
        options_lines = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)]
        options_section = f"选项：\n{'\n'.join(options_lines)}\n"

    # 构建题型部分
    type_section = ""
    if question_type and question_type != "unknown":
        type_map = {
            "single": "单选题",
            "multiple": "多选题",
            "judgement": "判断题",
            "completion": "填空题",
            "essay": "简答题",
            "analysis": "分析题",
        }
        type_name = type_map.get(question_type, "未知题型")
        type_section = f"题型：{type_name}\n"

    # 构建修正建议部分
    corrections_section = ""
    if corrections:
        corrections_section = f"用户修正建议：\n{corrections}\n"

    return REVIEW_USER_PROMPT_TEMPLATE.format(
        subject=subject,
        question=question,
        answer=answer,
        options_section=options_section,
        type_section=type_section,
        corrections_section=corrections_section,
    )


# 批量复审提示词
BATCH_REVIEW_PROMPT = """请批量审核以下题目的答案。

题目列表：
{questions}

答案列表：
{answers}

请对每个答案进行审核，返回 JSON 数组格式的审核结果。每个元素包含：
- question_index: 题目索引（从 0 开始）
- is_correct: 是否正确
- confidence: 置信度
- corrected_answer: 修正后的答案（如有必要）
- explanation: 审核说明
"""


# 专项审核提示词 - 针对特定题型
SPECIALIZED_REVIEW_PROMPTS = {
    "single": """请专门审核单选题答案。

题目：{question}
选项：{options}
答案：{answer}

审核要点：
1. 答案是否为单个选项字母（A/B/C/D）
2. 答案是否与正确选项匹配
3. 是否存在多选或漏选

返回 JSON 格式审核结果。""",
    "multiple": """请专门审核多选题答案。

题目：{question}
选项：{options}
答案：{answer}

审核要点：
1. 答案是否为多个选项字母的组合（如 AB/ABC）
2. 答案是否与正确选项匹配
3. 是否完整选择了所有正确选项

返回 JSON 格式审核结果。""",
    "judgement": """请专门审核判断题答案。

题目：{question}
答案：{answer}

审核要点：
1. 答案是否为"正确"或"错误"
2. 判断是否准确

返回 JSON 格式审核结果。""",
    "completion": """请专门审核填空题答案。

题目：{question}
答案：{answer}

审核要点：
1. 答案是否填入空白处
2. 答案是否准确无误
3. 表述是否规范

返回 JSON 格式审核结果。""",
}


# 答案质量评估提示词
ANSWER_QUALITY_EVAL_PROMPT = """请评估以下答案的质量。

题目：{question}
答案：{answer}

评估维度：
1. 完整性：答案是否完整回答了问题
2. 准确性：答案是否准确无误
3. 简洁性：答案是否简洁明了
4. 规范性：表述是否规范

请返回 JSON 格式：
{{
    "completeness_score": 1-5 分，
    "accuracy_score": 1-5 分，
    "conciseness_score": 1-5 分，
    "standardization_score": 1-5 分，
    "overall_score": 总体评分 1-5 分，
    "comments": "具体评价和改进建议"
}}
"""
