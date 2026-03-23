"""
API v2 版本 Schema 定义
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from schemas.common import BaseResponse

# ========== 分类相关模型 ==========


class CategoryCreate(BaseModel):
    """创建分类请求"""

    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")


class CategoryAssign(BaseModel):
    """分配题目到分类请求"""

    category_ids: List[int] = Field(..., description="分类 ID 列表")


class CategoryResult(BaseModel):
    """AI 分类结果"""

    category_id: int = Field(..., description="分类 ID")
    confidence: float = Field(..., description="置信度，0.0-1.0")
    reason: str = Field(..., description="分类理由")


class CategoryData(BaseModel):
    """分类数据响应"""

    id: int = Field(..., description="分类 ID")
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")


class CategoryListResponse(BaseResponse):
    """分类列表响应"""

    data: List[CategoryData]


class CategoryAssignResponse(BaseResponse):
    """分配分类响应"""

    data: List[CategoryData] = Field(default_factory=list)


class CategoryAIResponse(BaseResponse):
    """AI 分类结果响应"""

    data: List[CategoryResult] = Field(default_factory=list)
