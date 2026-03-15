"""
API Token 模型
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
import enum
from sqlmodel import Field, Relationship, Column
from sqlalchemy import Enum
from utils.access_token import generate_api_key
from . import BaseModel

if TYPE_CHECKING:
    from .query_log import QueryLog


class TokenStatus(str, enum.Enum):
    """Token 状态枚举"""

    ACTIVE = "active"
    DISABLED = "disabled"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"


class ApiKey(BaseModel, table=True):
    """API 用户凭证表"""

    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True, default_factory=generate_api_key)
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    total_queries: int = Field(default=0)
    success_queries: int = Field(default=0)
    remaining_queries: int = Field(default=1000)
    status: str = Field(default=TokenStatus.ACTIVE, sa_column=Column(Enum(TokenStatus)))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 关联查询日志
    query_logs: list["QueryLog"] = Relationship(back_populates="token")
