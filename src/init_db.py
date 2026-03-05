"""
数据库初始化脚本
用于创建测试数据和初始配置
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from db import db, VectorStore
from agents.rag_chat import rag_chat


def init_database():
    """初始化数据库并添加测试数据"""
    print("=" * 60)
    print("开始初始化数据库...")
    print("=" * 60)
    
    # 1. 创建测试 Token
    print("\n1. 创建测试 Token...")
    test_tokens = [
        ("test123456", 1000),
        ("demo789012", 500),
        ("user345678", 100),
    ]
    
    for token_str, remaining in test_tokens:
        try:
            token_info = db.create_token(token_str, remaining)
            print(f"   ✓ Token '{token_str}' 创建成功 (剩余次数：{token_info['remaining_queries']})")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                print(f"   ⚠ Token '{token_str}' 已存在，跳过")
            else:
                print(f"   ✗ 创建失败：{e}")
    
    # 2. 创建分类
    print("\n2. 创建题目分类...")
    categories = [
        ("政治理论", "马克思主义基本原理、毛泽东思想等"),
        ("历史文化", "中国历史、世界历史、文化知识"),
        ("科学技术", "自然科学、技术工程、科普知识"),
        ("法律法规", "宪法、法律、法规条例"),
        ("经济社会", "经济理论、社会发展、时事政治"),
        ("教育心理", "教育学、心理学、教师职业"),
    ]
    
    category_ids = []
    for name, description in categories:
        try:
            cat_id = db.create_category(name, description)
            category_ids.append(cat_id)
            print(f"   ✓ 分类 '{name}' 创建成功 (ID: {cat_id})")
        except Exception as e:
            print(f"   ✗ 创建失败：{e}")
    
    # 3. 添加示例题目
    print("\n3. 添加示例题目到题库...")
    sample_questions = [
        {
            "question": "中国梦的本质是什么？",
            "answer": "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库"
        },
        {
            "question": "马克思主义活的灵魂是？",
            "answer": "具体问题具体分析",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库"
        },
        {
            "question": "我国根本的政治制度是？",
            "answer": "人民代表大会制度",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库"
        },
        {
            "question": "抗日战争爆发于哪一年？",
            "answer": "1937 年",
            "category_id": 1,
            "is_ai_generated": False,
            "source": "历史文化题库"
        },
        {
            "question": "光在真空中的传播速度是多少？",
            "answer": "约 3×10^8 米/秒（299,792,458 米/秒）",
            "category_id": 2,
            "is_ai_generated": False,
            "source": "科学技术题库"
        },
        {
            "question": "我国的最高国家权力机关是？",
            "answer": "全国人民代表大会",
            "category_id": 3,
            "is_ai_generated": False,
            "source": "法律法规题库"
        },
        {
            "question": "新发展理念包括哪些内容？",
            "answer": "创新、协调、绿色、开放、共享",
            "category_id": 4,
            "is_ai_generated": False,
            "source": "经济社会题库"
        },
        {
            "question": "教育的根本任务是？",
            "answer": "立德树人",
            "category_id": 5,
            "is_ai_generated": False,
            "source": "教育心理题库"
        },
    ]
    
    question_ids = []
    for q in sample_questions:
        try:
            q_id = db.add_question(
                question_text=q["question"],
                answer_text=q["answer"],
                is_ai_generated=q["is_ai_generated"],
                source=q["source"]
            )
            question_ids.append(q_id)
            
            # 分配到对应分类
            if q["category_id"] < len(category_ids):
                db.assign_category(q_id, category_ids[q["category_id"]])
            
            print(f"   ✓ 题目 '{q['question'][:20]}...' 添加成功 (ID: {q_id})")
        except Exception as e:
            print(f"   ✗ 添加失败：{e}")
    
    # 4. 添加到向量库
    print("\n4. 将题目添加到向量库...")
    for i, q in enumerate(sample_questions):
        try:
            rag_chat.add_document(
                question=q["question"],
                answer=q["answer"],
                metadata={
                    "question_id": question_ids[i],
                    "source": q["source"]
                }
            )
            print(f"   ✓ 题目 '{q['question'][:20]}...' 已向量化")
        except Exception as e:
            print(f"   ✗ 向量化失败：{e}")
    
    # 5. 记录日志
    print("\n" + "=" * 60)
    print("数据库初始化完成！")
    print("=" * 60)
    print(f"\n统计信息:")
    print(f"  - Token 数量：{len(test_tokens)}")
    print(f"  - 分类数量：{len(categories)}")
    print(f"  - 题目数量：{len(sample_questions)}")
    print(f"\n测试 Token:")
    for token_str, _ in test_tokens:
        print(f"  - {token_str}")
    print("\n提示：可以使用这些 Token 调用 API 进行测试")
    print("=" * 60)


if __name__ == "__main__":
    init_database()
