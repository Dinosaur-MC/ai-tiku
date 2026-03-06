"""
Query Log 模型
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from .token import ApiToken


class QueryLog(SQLModel, table=True):
    """查询日志表"""
    __tablename__ = "query_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token_id: int = Field(foreign_key="api_tokens.id", index=True)
    query_text: str = Field()
    found: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关联 token
    token: Optional["ApiToken"] = Relationship(back_populates="query_logs")
