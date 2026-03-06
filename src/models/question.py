"""
Question 模型
"""

from . import BaseModel
from sqlmodel import Field, Relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .question_category import QuestionCategory


class Question(BaseModel, table=True):
    """题库主表"""

    __tablename__ = "questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_text: str = Field(index=True)
    answer_text: str = Field()
    is_ai_generated: bool = Field(default=False)
    source: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 关联分类（通过关联表）
    categories: list["QuestionCategory"] = Relationship(back_populates="question")
