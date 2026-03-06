"""
API Token 模型
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .query_log import QueryLog


class ApiToken(SQLModel, table=True):
    """API 用户凭证表"""

    __tablename__ = "api_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    total_queries: int = Field(default=0)
    success_queries: int = Field(default=0)
    remaining_queries: int = Field(default=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # 关联查询日志
    query_logs: list["QueryLog"] = Relationship(back_populates="token")
