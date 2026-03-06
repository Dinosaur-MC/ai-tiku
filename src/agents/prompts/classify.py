"""
题目分类提示词模板
用于指导 LLM 将题目自动分类到合适的类别
"""

CLASSIFICATION_SYSTEM_PROMPT = """你是一个专业的题库分类助手。你的任务是根据题目的内容和特征，将其分类到最合适的类别中。

分类原则：
1. 仔细分析题目的关键词、主题和考查的知识点
2. 考虑题目所属的学科领域
3. 参考题目的难度等级和题型特点
4. 如果题目涉及多个领域，选择最主要的一个

输出格式要求：
请返回 JSON 数组格式，每个元素包含：
- category_id: 类别 ID（整数）
- confidence: 置信度（0-1 之间的浮点数，保留两位小数）
- reason: 分类理由（简明扼要，不超过 50 字）

示例输出：
[
    {
        "category_id": 1,
        "confidence": 0.95,
        "reason": "题目考查马克思主义基本原理中的矛盾论"
    }
]
"""

CLASSIFICATION_USER_PROMPT_TEMPLATE = """请分析以下题目并进行分类。

可用类别列表：
{categories}

题目内容：
{question}

{options_section}

{type_section}

请根据上述信息，对题目进行分类。返回 JSON 数组格式的结果。"""


def build_classification_prompt(categories: list, question: str, 
                               options: list = None, question_type: str = None) -> str:
    """
    构建完整的分类提示词
    
    Args:
        categories: 可用类别列表，每个元素为 dict，包含 id, name, description
        question: 题目内容
        options: 选项列表（可选）
        question_type: 题目类型（可选）
    
    Returns:
        完整的提示词字符串
    """
    # 构建类别描述
    categories_str = "\n".join([
        f"- {cat['id']}: {cat['name']} ({cat.get('description', '')})"
        for cat in categories
    ])
    
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
            "analysis": "分析题"
        }
        type_name = type_map.get(question_type, "未知题型")
        type_section = f"题型：{type_name}\n"
    
    return CLASSIFICATION_USER_PROMPT_TEMPLATE.format(
        categories=categories_str,
        question=question,
        options_section=options_section,
        type_section=type_section
    )


# 分类后处理提示词
POST_CLASSIFICATION_PROMPT = """请检查以下分类结果是否合理：

题目：{question}
分类结果：{result}

如果分类结果不合理，请提供修正建议。返回 JSON 格式：
{{
    "is_reasonable": true/false,
    "suggested_category_id": 建议的类别 ID（如有必要）,
    "reason": "说明理由"
}}
"""
