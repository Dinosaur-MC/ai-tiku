"""
数据库模型基类
"""

from sqlmodel import SQLModel, Field
from datetime import datetime, timezone


class BaseModel(SQLModel):
    """基础模型，包含通用字段"""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
