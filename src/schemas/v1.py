"""
API v1 版本 Schema 定义
保持与现有 API 完全兼容
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict
from schemas.common import BaseResponse


# ========== 请求模型 ==========


class QueryRequest(BaseModel):
    """查询请求模型"""

    title: Optional[str] = Field(None, description="题目内容（与 q、question 三选一）")
    q: Optional[str] = Field(None, description="题目内容（与 title、question 三选一）")
    question: Optional[str] = Field(None, description="题目内容（与 title、q 三选一）")
    options: Optional[str] = Field(None, description="选项内容，多个用换行符分隔")
    type: Optional[str] = Field("unknown", description="题目类型")
    more: Optional[bool] = Field(False, description="是否返回多个结果（已禁用）")
    stream: bool = Field(False, description="是否使用 SSE 流式返回结果")

    def get_question_text(self) -> str:
        """获取题目文本（优先级：title> q > question）"""
        return self.title or self.q or self.question or ""

    def get_options_list(self) -> Optional[List[str]]:
        """解析选项列表"""
        if not self.options:
            return None
        return [opt.strip() for opt in self.options.split("\n") if opt.strip()]


# ========== 响应数据模型 ==========


class SingleResultData(BaseModel):
    """单条结果数据模型"""

    question: str
    answer: str
    times: int
    ai: bool = False


class MultiResultItem(BaseModel):
    """多条结果中的单项"""

    question: str
    answer: str
    ai: bool = False


class MultiResultData(BaseModel):
    """多条结果数据模型"""

    results: List[MultiResultItem]
    times: int


# ========== 完整响应模型 ==========


class QueryResponse(BaseResponse):
    """查询响应模型"""

    data: Union[SingleResultData, MultiResultData]

    class Config:
        json_schema_extra = {
            "example": {
                "code": 1,
                "message": "请求成功",
                "data": {
                    "question": "中国梦的本质是什么？",
                    "answer": "实现中华民族伟大复兴",
                    "times": 999,
                    "ai": False,
                },
            }
        }


class InfoResponse(BaseResponse):
    """题库信息响应模型"""

    data: Dict[str, int]

    class Config:
        json_schema_extra = {
            "example": {
                "code": 1,
                "message": "请求成功",
                "data": {"times": 1000, "user_times": 100, "success_times": 95},
            }
        }
