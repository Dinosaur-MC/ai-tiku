"""
题目查询提示词模板
用于指导 LLM 准确回答题目或生成答案
"""

QUERY_SYSTEM_PROMPT = """你是一个专业的题库答题助手。你的任务是根据用户提供的题目，给出准确、简洁的答案。

答题原则：
1. 准确性：确保答案正确无误
2. 简洁性：直接给出答案，不要冗长解释
3. 规范性：按照题型要求作答
   - 选择题：只给出选项字母（如：A 或 AB）
   - 判断题：只给出"正确"或"错误"
   - 填空题：给出具体的填空内容
   - 简答题：给出核心要点
4. 如果无法确定答案，诚实地表示不知道

输出格式：
- 直接输出答案内容，不需要额外的说明或解释
- 选择题只需输出选项字母
- 判断题输出"正确"或"错误"
- 其他题型输出具体答案
"""

QUERY_USER_PROMPT_TEMPLATE = """请回答以下问题：

题目：{question}

{options_section}

{type_section}

请直接给出答案，不需要解释。"""


def build_query_prompt(question: str, options: list = None, 
                      question_type: str = "unknown") -> str:
    """
    构建完整的查询提示词
    
    Args:
        question: 题目内容
        options: 选项列表（可选）
        question_type: 题目类型
    
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
            "unknown": "未知题型"
        }
        type_name = type_map.get(question_type, "未知题型")
        type_section = f"题型：{type_name}\n"
    
    return QUERY_USER_PROMPT_TEMPLATE.format(
        question=question,
        options_section=options_section,
        type_section=type_section
    )


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


# 带置信度的答案生成提示词
CONFIDENCE_ANSWER_PROMPT = """请回答以下问题，并评估你对答案的置信度。

题目：{question}

{options_section}

请返回 JSON 格式：
{{
    "answer": "你的答案",
    "confidence": 0.0-1.0 之间的浮点数，
    "reasoning": "简要说明答案的依据"
}}
"""
