"""
Question-Category 关联模型
"""

from sqlmodel import Field, Relationship
from typing import TYPE_CHECKING
from . import BaseModel

if TYPE_CHECKING:
    from .question import Question
    from .category import Category


class QuestionCategory(BaseModel, table=True):
    """题目 - 分类关联表（多对多）"""

    __tablename__ = "question_category"

    question_id: int = Field(foreign_key="questions.id", primary_key=True)
    category_id: int = Field(foreign_key="categories.id", primary_key=True)

    # 关联关系
    question: "Question" = Relationship(back_populates="categories")
    category: "Category" = Relationship(back_populates="questions")
