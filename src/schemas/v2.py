"""
API v2 版本 Schema 定义
更清晰、更规范的 API 设计
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from schemas.common import BaseResponse


# ========== 枚举类型 ==========


class QuestionType(str, Enum):
    """题目类型枚举"""

    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGEMENT = "judgement"
    COMPLETION = "completion"
    ESSAY = "essay"
    UNKNOWN = "unknown"


class SearchMode(str, Enum):
    """搜索模式枚举"""

    EXACT = "exact"  # 精确匹配
    FUZZY = "fuzzy"  # 模糊搜索
    AI_ONLY = "ai_only"  # 仅 AI 生成


# ========== 请求模型 ==========


class QueryRequest(BaseModel):
    """查询请求模型 - v2 优化版"""

    question: str = Field(..., description="题目内容", min_length=1)
    options: Optional[List[str]] = Field(None, description="选项列表")
    question_type: QuestionType = Field(
        default=QuestionType.UNKNOWN, description="题目类型"
    )
    search_mode: SearchMode = Field(default=SearchMode.FUZZY, description="搜索模式")
    max_results: int = Field(default=1, ge=1, le=10, description="最大返回结果数")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "中国梦的本质是什么？",
                "options": ["A. 国家富强", "B. 民族振兴", "C. 人民幸福"],
                "question_type": "single",
                "search_mode": "fuzzy",
                "max_results": 1,
            }
        }


# ========== 响应数据模型 ==========


class AnswerData(BaseModel):
    """答案数据模型"""

    question: str = Field(description="题目")
    answer: str = Field(description="答案")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="置信度（AI 生成时有效）"
    )
    source: str = Field(default="database", description="来源：database/ai")
    matched_at: Optional[datetime] = Field(
        None, description="匹配时间（数据库来源时有效）"
    )


class TokenUsage(BaseModel):
    """Token 使用统计"""

    remaining: int = Field(description="剩余次数")
    total_used: int = Field(description="总使用次数")
    success_count: int = Field(description="成功次数")


# ========== 完整响应模型 ==========


class QueryResponse(BaseResponse):
    """查询响应模型 - v2"""

    data: AnswerData
    usage: TokenUsage

    class Config:
        json_schema_extra = {
            "example": {
                "code": 1,
                "message": "请求成功",
                "data": {
                    "question": "中国梦的本质是什么？",
                    "answer": "实现中华民族伟大复兴",
                    "confidence": 0.98,
                    "source": "database",
                    "matched_at": "2024-01-01T12:00:00Z",
                },
                "usage": {"remaining": 999, "total_used": 100, "success_count": 95},
            }
        }


class InfoResponse(BaseResponse):
    """题库信息响应模型 - v2"""

    data: TokenUsage

    class Config:
        json_schema_extra = {
            "example": {
                "code": 1,
                "message": "请求成功",
                "data": {"remaining": 1000, "total_used": 100, "success_count": 95},
            }
        }
