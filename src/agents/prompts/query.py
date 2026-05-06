"""
题目查询提示词模板
用于指导 LLM 准确回答题目或生成答案
"""

from typing import Dict, Optional

# QUERY_OUTPUT_CHECK_REGEX
# Regex patterns to validate the output format based on question type
QUERY_OUTPUT_CHECK_REGEX: Dict[str, str] = {
    "single": r"^[A-Z]$",  # Exactly one uppercase letter
    "multiple": r"^[A-Z]+$",  # One or more uppercase letters (e.g., A, AB, ABC)
    "judgement": r"^[TF]$",  # Exactly 'T' or 'F'
    "completion": r"^[^：。？\s][^：。？]*$",  # No colon, period, or sentence-ending punctuation at start
    "essay": r"^.{50,}$",  # At least 50 characters for essay type
}


# TYPE_DETECTION_PROMPT_TEMPLATE
TYPE_DETECTION_PROMPT_TEMPLATE = """
You are an AI classifier. Detect the question type based on the provided text and options.

Available type names: 'single', 'multiple', 'judgement', 'completion', 'essay'.

Rules:

1. If options exist (A/B/C/D or 1/2/3/4) and only one answer is expected -> 'single'.
2. If options exist and multiple answers are expected -> 'multiple'.
3. If the question asks for True/False or Correct/Incorrect -> 'judgement'.
4. If the question contains blanks (____) to fill -> 'completion'.
5. If the question requires a long descriptive answer, analysis, or discussion -> 'essay'.
   Note: Sometimes essay questions are labeled as completion. If the expected answer length is long, classify as 'essay'.
6. Output ONLY the type name (lowercase).

Examples:

User: 
Title:  Python 是什么类型的语言？
Options: A. 编译型 B. 解释型 C. 汇编 D. 机器
Type:
single

User: 
Title:  下列说法正确的是？
Options: A. 地球是平的 B. 地球是圆的
Type:
single

User: 
Title:  请简述人工智能的发展历程。
Options: None
Type:
essay

User: 
Title:  水的化学式是____。
Options: None
Type:
completion

Current Task:

Title: {title}
Options: {options}
Type:
"""

# QUERY_SINGLE_PROMPT_TEMPLATE
QUERY_SINGLE_PROMPT_TEMPLATE = """
You are an AI exam assistant. Solve the following single-choice question.
Rules:
1. Analyze the question and options carefully.
2. Output ONLY the option letter (e.g., A, B, C, D).
3. Do not output any explanation or extra text.
4. Language: Simplified Chinese for reasoning, but Output MUST be English letter.
5. Return `None` if the question cannot be answered.

Example:

Subject: 数学
Title: 1 + 1 等于多少？
Options: A. 1 B. 2 C. 3 D. 4
Answer:
B

Current Task:

Subject: {subject}
Title: {title}
Options: {options}
Answer:
"""

# QUERY_MULTIPLE_PROMPT_TEMPLATE
QUERY_MULTIPLE_PROMPT_TEMPLATE = """
You are an AI exam assistant. Solve the following multiple-choice question.

Rules:

1. Analyze the question and options carefully.
2. Select ALL correct options.
3. Output ONLY the option letters concatenated (e.g., AB, ABC, ACD).
4. Do not output any explanation or extra text.
5. Language: Simplified Chinese for reasoning, but Output MUST be English letters.
6. Return `None` if the question cannot be answered.

Example:

Subject: 计算机程序设计基础
Title: 以下哪些是编程语言？
Options: A. Python B. HTML C. Java D. CSS
Answer:
AC

Current Task:

Subject: {subject}
Title: {title}
Options: {options}
Answer:
"""

# QUERY_JUDGEMENT_PROMPT_TEMPLATE
QUERY_JUDGEMENT_PROMPT_TEMPLATE = """
You are an AI exam assistant. Solve the following judgement question.

Rules:

1. Determine if the statement is True or False.
2. Output ONLY 'T' for True or 'F' for False.
3. Do not output any explanation or extra text.
4. Return `None` if the question cannot be answered.

Example:

Subject: 科学
Question: 地球是太阳系中最大的行星。
Answer:
F

Current Task:

Subject: {subject}
Question: {title}
Answer:
"""

# QUERY_COMPLETION_PROMPT_TEMPLATE
QUERY_COMPLETION_PROMPT_TEMPLATE = """
You are an AI exam assistant. Solve the following fill-in-the-blank question.

Rules:

1. Output ONLY the exact content that should fill each blank and no extra content.
2. DO NOT include the question text, prefixes, suffixes or explanations.
3. DO NOT output phrases like "答案是", "填空:", "答案:", etc.
4. If there are multiple blanks, separate answers with '#' ONLY.
5. Prefer using terminologies and scientific terms in your answer.
6. Return `None` if the question cannot be answered.

Example 1:

Subject: 地理
Question: 中国的首都是____，简称____。
Answer:
北京#京

Example 2:

Subject: 计算机组成原理
Question: 冯·诺依曼体系结构主要包括以下几种部件____、____、____、____、____。
Answer:
运算器#控制器#存储器#输入设备#输出设备

Current Task:

Subject: {subject}
Question: {title}
Answer:
"""

# QUERY_ESSAY_PROMPT_TEMPLATE
QUERY_ESSAY_PROMPT_TEMPLATE = """
You are an AI exam assistant. Write an answer for the following essay question.

Rules:

1. Provide a structured, paragraph-based reply (1~3 paragraphs).
2. The answer must be detailed and exceed 50 Chinese characters.
3. Do not output any labels like 'Answer:', just the content.
4. Language: Simplified Chinese.
5. Return `None` if the question cannot be answered.

Example:

Subject: 物理
Question: 请简述牛顿第一定律。
Answer:
牛顿第一定律，又称惯性定律，表明任何物体都要保持匀速直线运动或静止状态，直到外力迫使它改变运动状态为止。这一定律揭示了力和运动的关系，指出力不是维持物体运动的原因，而是改变物体运动状态的原因。惯性是物体固有的属性，质量是惯性大小的量度。

Current Task:

Subject: {subject}
Question: {title}
Answer:
"""

# QUERY_CORRECTION_PROMPT_TEMPLATE
QUERY_CORRECTION_PROMPT_TEMPLATE = """
You are an AI format corrector. Your previous output failed the format validation.

Rules:

1. Keep the original answer content as much as possible.
2. Reformat the output to strictly match the required format.
3. Output ONLY the corrected answer.

Examples:

Question Type: single
Required Format: ^[A-Z]$
Your Previous Output: 答案是 A
Corrected: A

Question Type: completion
Required Format: ^.+$ (use # for multiple)
Your Previous Output: 第一个空填北京，第二个空填京
Corrected: 北京#京

Current Task:

Question Type: {question_type}
Required Format: {format_requirement}
Your Previous Output: {previous_output}
Corrected:
"""


def build_type_detection_prompt(title: str, options: Optional[str]) -> str:
    """Builds the prompt for question type detection."""
    return TYPE_DETECTION_PROMPT_TEMPLATE.format(title=title, options=options)


def build_query_prompt(question_type: str, title: str, options: Optional[str], subject: Optional[str]) -> str:
    """Builds the prompt for answering the question based on type."""
    templates = {
        "single": QUERY_SINGLE_PROMPT_TEMPLATE,
        "multiple": QUERY_MULTIPLE_PROMPT_TEMPLATE,
        "judgement": QUERY_JUDGEMENT_PROMPT_TEMPLATE,
        "completion": QUERY_COMPLETION_PROMPT_TEMPLATE,
        "essay": QUERY_ESSAY_PROMPT_TEMPLATE,
    }
    template = templates.get(question_type, QUERY_COMPLETION_PROMPT_TEMPLATE)
    return template.format(subject=subject, title=title, options=options)


def build_correction_prompt(question_type: str, previous_output: str) -> str:
    """Builds the prompt for correcting format errors."""
    req_regex = QUERY_OUTPUT_CHECK_REGEX.get(question_type, r".+")
    return QUERY_CORRECTION_PROMPT_TEMPLATE.format(
        question_type=question_type,
        format_requirement=req_regex,
        previous_output=previous_output,
    )
