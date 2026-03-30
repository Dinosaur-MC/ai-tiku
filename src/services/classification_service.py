"""
题目分类管理服务
提供分类的增删改查、题目分类关联、向量库同步等功能
"""

from typing import List, Optional, Dict
from sqlmodel import Session, select

from models import Category, QuestionCategory, Question
from utils.dbc import db, VectorStore


class ClassificationService:
    """题目分类管理服务类"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session if session else db.get_session()

    def get_all_categories(self) -> List[Dict]:
        """
        获取所有可用分类

        Returns:
            分类列表，每个分类包含 id, name, description
        """
        statement = select(Category)
        categories = self.session.exec(statement).all()
        
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
            }
            for cat in categories
        ]

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        根据 ID 获取分类

        Args:
            category_id: 分类 ID

        Returns:
            分类对象，不存在则返回 None
        """
        return self.session.get(Category, category_id)

    def create_category(
        self, name: str, description: Optional[str] = None
    ) -> Category:
        """
        创建新分类

        Args:
            name: 分类名称
            description: 分类描述

        Returns:
            创建的分类对象
        """
        # 检查是否已存在同名分类
        existing = self.session.exec(
            select(Category).where(Category.name == name)
        ).first()
        
        if existing:
            raise ValueError(f"分类 '{name}' 已存在")

        category = Category(name=name, description=description)
        category = db.create(category)
        
        return category

    def delete_category(self, category_id: int) -> bool:
        """
        删除分类

        Args:
            category_id: 分类 ID

        Returns:
            True 表示删除成功，False 表示分类不存在
        """
        category = self.get_category_by_id(category_id)
        if not category:
            return False

        # 删除所有关联的题目 - 分类关系
        relations = self.session.exec(
            select(QuestionCategory).where(
                QuestionCategory.category_id == category_id
            )
        )
        for relation in relations:
            self.session.delete(relation)

        # 删除分类
        self.session.delete(category)
        self.session.commit()

        return True

    def assign_to_question(
        self, question_id: int, category_ids: List[int]
    ) -> List[QuestionCategory]:
        """
        将题目分配到多个分类

        Args:
            question_id: 题目 ID
            category_ids: 分类 ID 列表

        Returns:
            创建的关联对象列表
        """
        # 验证题目是否存在
        question = self.session.get(Question, question_id)
        if not question:
            raise ValueError(f"题目 {question_id} 不存在")

        # 验证所有分类是否存在
        for cat_id in category_ids:
            if not self.get_category_by_id(cat_id):
                raise ValueError(f"分类 {cat_id} 不存在")

        # 删除旧的关联
        old_relations = self.session.exec(
            select(QuestionCategory).where(
                QuestionCategory.question_id == question_id
            )
        )
        for relation in old_relations:
            self.session.delete(relation)

        # 创建新的关联
        relations = []
        for cat_id in category_ids:
            relation = QuestionCategory(
                question_id=question_id, category_id=cat_id
            )
            relations.append(relation)

        # 批量保存
        db.create_many(relations)

        # 更新向量库（按分类索引）
        self._sync_vector_store(question, category_ids)

        return relations

    def _sync_vector_store(self, question: Question, category_ids: List[int]):
        """
        同步向量库（按分类更新索引）

        Args:
            question: 题目对象
            category_ids: 分类 ID 列表
        """
        # 为每个分类更新向量库
        for cat_id in category_ids:
            category = self.get_category_by_id(cat_id)
            vector_store = VectorStore(
                category_id=cat_id, 
                category_name=category.name if category else None
            )
            vector_store.add_documents([question])

    def get_categories_for_question(
        self, question_id: int
    ) -> List[Dict]:
        """
        获取题目的所有分类

        Args:
            question_id: 题目 ID

        Returns:
            分类列表，每个包含 id, name, description
        """
        statement = select(QuestionCategory).where(
            QuestionCategory.question_id == question_id
        )
        question_categories = self.session.exec(statement).all()

        categories = []
        for qc in question_categories:
            category = self.get_category_by_id(qc.category_id)
            if category:
                categories.append({
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                })

        return categories

    def get_questions_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """
        获取指定分类下的题目列表

        Args:
            category_id: 分类 ID
            skip: 跳过记录数
            limit: 返回记录数限制

        Returns:
            题目列表
        """
        # 先找到该分类下的所有题目 ID
        statement = select(QuestionCategory).where(
            QuestionCategory.category_id == category_id
        )
        question_categories = self.session.exec(statement).all()

        question_ids = [qc.question_id for qc in question_categories]

        # 获取题目详情
        questions_statement = select(Question).where(
            Question.id.in_(question_ids)
        ).offset(skip).limit(limit)

        return self.session.exec(questions_statement).all()

    def remove_from_question(
        self, question_id: int, category_id: int
    ) -> bool:
        """
        从题目移除分类关联

        Args:
            question_id: 题目 ID
            category_id: 分类 ID

        Returns:
            True 表示移除成功，False 表示关联不存在
        """
        relation = self.session.exec(
            select(QuestionCategory).where(
                QuestionCategory.question_id == question_id,
                QuestionCategory.category_id == category_id,
            )
        ).first()

        if not relation:
            return False

        self.session.delete(relation)
        self.session.commit()

        return True


# 单例模式
classification_service = ClassificationService()
