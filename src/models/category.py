"""
Category 模型
"""

from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from . import BaseModel

if TYPE_CHECKING:
    from .question_category import QuestionCategory


class Category(BaseModel, table=True):
    """分类表"""

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = Field(default=None)

    # 关联题目分类
    questions: list["QuestionCategory"] = Relationship(back_populates="category")
