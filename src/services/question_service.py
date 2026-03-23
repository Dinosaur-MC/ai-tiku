"""
题目管理服务
提供题目的增删改查等管理功能
"""

from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime

from models import Question, QuestionType, ReviewStatus, QuestionCategory
from utils.dbc import db, VectorStore


class QuestionService:
    """题目管理服务类"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session if session else db.get_session()

    def create_question(
        self,
        question_title: str,
        answer_text: str,
        question_type: QuestionType = QuestionType.UNKNOWN,
        question_options: Optional[str] = None,
        is_ai_generated: bool = False,
        review_status: ReviewStatus = ReviewStatus.PENDING,
        source: Optional[str] = None,
        category_ids: Optional[List[int]] = None,
    ) -> Question:
        """
        创建新题目

        Args:
            question_title: 题目标题/题干
            answer_text: 答案文本
            question_type: 题目类型
            question_options: 选项（选择题需要）
            is_ai_generated: 是否 AI 生成
            review_status: 审核状态
            source: 题目来源
            category_ids: 分类 ID 列表

        Returns:
            创建的题目对象
        """
        question = Question(
            question_title=question_title,
            answer_text=answer_text,
            question_type=question_type,
            question_options=question_options,
            is_ai_generated=is_ai_generated,
            review_status=review_status,
            source=source,
        )

        # 保存到数据库
        question = db.create(question)

        # 添加到向量库
        vector_store = VectorStore()
        vector_store.add_documents([question])

        # 如果指定了分类，创建关联
        if category_ids:
            for category_id in category_ids:
                category_link = QuestionCategory(
                    question_id=question.id, category_id=category_id
                )
                db.create(category_link)

        return question

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """
        根据 ID 获取题目

        Args:
            question_id: 题目 ID

        Returns:
            题目对象，不存在则返回 None
        """
        return self.session.get(Question, question_id)

    def get_questions(
        self,
        skip: int = 0,
        limit: int = 100,
        question_type: Optional[QuestionType] = None,
        review_status: Optional[ReviewStatus] = None,
        is_ai_generated: Optional[bool] = None,
        search_keyword: Optional[str] = None,
    ) -> List[Question]:
        """
        获取题目列表（支持分页和过滤）

        Args:
            skip: 跳过记录数
            limit: 返回记录数限制
            question_type: 题目类型过滤
            review_status: 审核状态过滤
            is_ai_generated: 是否 AI 生成过滤
            search_keyword: 搜索关键词

        Returns:
            题目列表
        """
        statement = select(Question)

        # 应用过滤条件
        if question_type is not None:
            statement = statement.where(Question.question_type == question_type)

        if review_status is not None:
            statement = statement.where(Question.review_status == review_status)

        if is_ai_generated is not None:
            statement = statement.where(Question.is_ai_generated == is_ai_generated)

        if search_keyword:
            statement = statement.where(search_keyword in Question.question_title)

        # 分页
        statement = statement.offset(skip).limit(limit)

        results = self.session.exec(statement)
        return results.all()

    def update_question(
        self,
        question_id: int,
        question_title: Optional[str] = None,
        answer_text: Optional[str] = None,
        question_type: Optional[QuestionType] = None,
        question_options: Optional[str] = None,
        review_status: Optional[ReviewStatus] = None,
        source: Optional[str] = None,
    ) -> Optional[Question]:
        """
        更新题目信息

        Args:
            question_id: 题目 ID
            question_title: 新的题目标题
            answer_text: 新的答案
            question_type: 新的题目类型
            question_options: 新的选项
            review_status: 新的审核状态
            source: 新的来源

        Returns:
            更新后的题目对象，不存在则返回 None
        """
        question = self.get_question_by_id(question_id)
        if not question:
            return None

        # 更新字段
        update_data = {
            "question_title": question_title,
            "answer_text": answer_text,
            "question_type": question_type,
            "question_options": question_options,
            "review_status": review_status,
            "source": source,
        }

        for field, value in update_data.items():
            if value is not None:
                setattr(question, field, value)

        # 更新时间戳
        question.updated_at = datetime.now()

        db.create(question)  # 保存更改

        # 重新向量化
        vector_store = VectorStore()
        vector_store.add_documents([question])

        return question

    def delete_question(self, question_id: int) -> bool:
        """
        删除题目

        Args:
            question_id: 题目 ID

        Returns:
            True 表示删除成功，False 表示题目不存在
        """
        question = self.get_question_by_id(question_id)
        if not question:
            return False

        # 删除关联的分类
        categories = self.session.exec(
            select(QuestionCategory).where(QuestionCategory.question_id == question_id)
        )
        for category in categories:
            self.session.delete(category)

        # 删除题目
        self.session.delete(question)
        self.session.commit()

        # 从向量库中移除
        vector_store = VectorStore()
        vector_store.remove_documents([question_id])

        return True

    def batch_create_questions(self, questions_data: List[dict]) -> List[Question]:
        """
        批量创建题目

        Args:
            questions_data: 题目数据列表，每个元素为字典

        Returns:
            创建的题目列表
        """
        questions = []
        for data in questions_data:
            question = Question(**data)
            questions.append(question)

        # 批量保存
        created_questions = db.create_many(questions)

        # 批量添加到向量库
        vector_store = VectorStore()
        vector_store.add_documents(created_questions)

        return created_questions

    def search_similar_questions(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.7,
        question_type_filter: Optional[QuestionType] = None,
    ) -> List[dict]:
        """
        语义搜索相似题目

        Args:
            query: 查询文本
            k: 返回结果数量
            score_threshold: 相似度阈值
            question_type_filter: 题目类型过滤

        Returns:
            搜索结果列表，包含题目和相似度分数
        """
        vector_store = VectorStore()
        results = vector_store.similarity_search(
            query=query,
            k=k,
            question_type_filter=(
                question_type_filter.value if question_type_filter else None
            ),
            score_threshold=score_threshold,
        )
        return results

    def approve_question(self, question_id: int) -> Optional[Question]:
        """
        审核通过题目

        Args:
            question_id: 题目 ID

        Returns:
            更新后的题目对象
        """
        return self.update_question(
            question_id=question_id, review_status=ReviewStatus.APPROVED
        )

    def reject_question(self, question_id: int, reason: str = "") -> Optional[Question]:
        """
        拒绝题目

        Args:
            question_id: 题目 ID
            reason: 拒绝原因

        Returns:
            更新后的题目对象
        """
        return self.update_question(
            question_id=question_id, review_status=ReviewStatus.REJECTED
        )

    def get_statistics(self) -> dict:
        """
        获取题目统计信息

        Returns:
            统计数据字典
        """
        total = self.session.exec(select(Question)).all()

        stats = {
            "total_count": len(total),
            "by_type": {},
            "by_review_status": {},
            "ai_generated_count": 0,
        }

        for question in total:
            # 按类型统计
            type_key = question.question_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            # 按审核状态统计
            status_key = question.review_status.value
            stats["by_review_status"][status_key] = (
                stats["by_review_status"].get(status_key, 0) + 1
            )

            # AI 生成统计
            if question.is_ai_generated:
                stats["ai_generated_count"] += 1

        return stats


question_service = QuestionService()
