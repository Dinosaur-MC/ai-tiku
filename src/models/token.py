"""
API Token 模型
"""

from . import BaseModel
from sqlmodel import Field, Relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .query_log import QueryLog


class ApiToken(BaseModel, table=True):
    """API 用户凭证表"""

    __tablename__ = "api_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    total_queries: int = Field(default=0)
    success_queries: int = Field(default=0)
    remaining_queries: int = Field(default=1000)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 关联查询日志
    query_logs: list["QueryLog"] = Relationship(back_populates="token")
