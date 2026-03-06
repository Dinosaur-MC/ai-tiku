"""
提示词模板模块 - 导出所有提示词模板和构建函数
"""

# 查询提示词
from agents.prompts.query import (
    QUERY_SYSTEM_PROMPT,
    QUERY_USER_PROMPT_TEMPLATE,
    build_query_prompt,
    AI_GENERATE_PROMPT,
    CONVERSATIONAL_QUERY_PROMPT,
    CONFIDENCE_ANSWER_PROMPT
)

# 分类提示词
from agents.prompts.classify import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT_TEMPLATE,
    build_classification_prompt,
    POST_CLASSIFICATION_PROMPT
)

# 复审提示词
from agents.prompts.review import (
    REVIEW_SYSTEM_PROMPT,
    REVIEW_USER_PROMPT_TEMPLATE,
    build_review_prompt,
    BATCH_REVIEW_PROMPT,
    SPECIALIZED_REVIEW_PROMPTS,
    ANSWER_QUALITY_EVAL_PROMPT
)

__all__ = [
    # 查询相关
    'QUERY_SYSTEM_PROMPT',
    'QUERY_USER_PROMPT_TEMPLATE',
    'build_query_prompt',
    'AI_GENERATE_PROMPT',
    'CONVERSATIONAL_QUERY_PROMPT',
    'CONFIDENCE_ANSWER_PROMPT',
    
    # 分类相关
    'CLASSIFICATION_SYSTEM_PROMPT',
    'CLASSIFICATION_USER_PROMPT_TEMPLATE',
    'build_classification_prompt',
    'POST_CLASSIFICATION_PROMPT',
    
    # 复审相关
    'REVIEW_SYSTEM_PROMPT',
    'REVIEW_USER_PROMPT_TEMPLATE',
    'build_review_prompt',
    'BATCH_REVIEW_PROMPT',
    'SPECIALIZED_REVIEW_PROMPTS',
    'ANSWER_QUALITY_EVAL_PROMPT',
]
