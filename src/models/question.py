"""
Question 模型
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import Field, Relationship, Column
from sqlalchemy import Enum
import enum
from . import BaseModel

if TYPE_CHECKING:
    from .question_category import QuestionCategory


class QuestionType(str, enum.Enum):
    """题目类型枚举"""

    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGEMENT = "judgement"
    COMPLETION = "completion"
    ESSAY = "essay"
    UNKNOWN = "unknown"


class ReviewStatus(str, enum.Enum):
    """审核状态枚举"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Question(BaseModel, table=True):
    """题库主表"""

    __tablename__ = "questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_type: str = Field(
        default=QuestionType.UNKNOWN, sa_column=Column(Enum(QuestionType))
    )
    question_title: str = Field(index=True)
    question_options: Optional[str] = Field(default=None)
    answer_text: str = Field()
    is_ai_generated: bool = Field(default=False)
    review_status: str = Field(
        default=ReviewStatus.PENDING, sa_column=Column(Enum(ReviewStatus))
    )
    source: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 关联分类（通过关联表）
    categories: list["QuestionCategory"] = Relationship(back_populates="question")
