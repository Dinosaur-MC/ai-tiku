"""
Query Log 模型
"""

from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from . import BaseModel

if TYPE_CHECKING:
    from .token import ApiToken


class QueryLog(BaseModel, table=True):
    """查询日志表"""

    __tablename__ = "query_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="api_tokens.id", index=True)
    query_text: str = Field()
    found: bool = Field(default=False)

    # 关联 token
    token: Optional["ApiToken"] = Relationship(back_populates="query_logs")
