"""
测试 SQLModel 数据库模型
"""
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import db
from models import ApiToken, Question, Category, QueryLog


def test_models():
    """测试数据库模型"""
    print("=" * 60)
    print("开始测试 SQLModel 数据库模型")
    print("=" * 60)
    
    # 1. 测试 Token 操作
    print("\n1. 测试 Token 操作...")
    try:
        # 创建 token
        token = db.create_token("test_model_123", 500)
        print(f"   ✓ 创建 Token: {token.token}, 剩余：{token.remaining_queries}")
        
        # 查询 token
        token_info = db.get_token_by_value("test_model_123")
        print(f"   ✓ 查询 Token: {token_info.token}, ID: {token_info.id}")
        
        # 更新 token 使用
        db.update_token_usage(token_info.id, success=True)
        updated = db.get_token_info(token_info.id)
        print(f"   ✓ 更新后 - 总查询：{updated.total_queries}, 成功：{updated.success_queries}, 剩余：{updated.remaining_queries}")
    except Exception as e:
        print(f"   ✗ Token 测试失败：{e}")
    
    # 2. 测试 Category 操作
    print("\n2. 测试 Category 操作...")
    try:
        cat_id = db.create_category("测试分类", "用于测试 SQLModel")
        print(f"   ✓ 创建分类 ID: {cat_id}")
        
        categories = db.get_all_categories()
        print(f"   ✓ 获取所有分类数量：{len(categories)}")
    except Exception as e:
        print(f"   ✗ Category 测试失败：{e}")
    
    # 3. 测试 Question 操作
    print("\n3. 测试 Question 操作...")
    try:
        q_id = db.add_question(
            question_text="SQLModel 测试题目？",
            answer_text="这是使用 SQLModel ORM 的测试答案",
            is_ai_generated=False,
            source="测试数据"
        )
        print(f"   ✓ 创建题目 ID: {q_id}")
        
        # 搜索题目
        results = db.search_questions("SQLModel")
        print(f"   ✓ 搜索结果数量：{len(results)}")
        
        # 根据 ID 查询
        question = db.get_question_by_id(q_id)
        print(f"   ✓ 根据 ID 查询：{question.question_text[:30]}...")
        
        # 分配分类
        if cat_id:
            db.assign_category(q_id, cat_id)
            print(f"   ✓ 题目分配到分类")
    except Exception as e:
        print(f"   ✗ Question 测试失败：{e}")
    
    # 4. 测试 Query Log 操作
    print("\n4. 测试 Query Log 操作...")
    try:
        if token_info and q_id:
            db.log_query(
                token_id=token_info.id,
                query_text="SQLModel 测试查询",
                found=True
            )
            print(f"   ✓ 记录查询日志")
    except Exception as e:
        print(f"   ✗ Query Log 测试失败：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_models()
