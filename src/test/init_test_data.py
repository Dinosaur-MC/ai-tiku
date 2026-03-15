"""
测试数据初始化脚本
用于创建测试数据和初始配置
注意：此文件仅用于测试目的，生产环境不应使用
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.dbc import db, VectorStore
from models import *
from sqlmodel import Session, select


def init_test_data():
    """初始化测试数据"""
    print("=" * 60)
    print("开始初始化测试数据...")
    print("=" * 60)

    # 1. 创建测试用户
    print("\n1. 创建测试用户...")
    test_users = [
        ("admin", "admin123", "admin@example.com", UserRole.ADMIN),
        ("user1", "password123", "user1@example.com", UserRole.USER),
        ("user2", "password456", "user2@example.com", UserRole.USER),
    ]

    for username, password, email, role in test_users:
        try:
            with db.get_session() as session:
                # 检查用户是否已存在
                statement = select(User).where(User.username == username)
                existing_user = session.exec(statement).first()

                if existing_user:
                    print(f"   ⚠ 用户 '{username}' 已存在，跳过")
                else:
                    new_user = User(
                        username=username, password=password, email=email, role=role
                    )
                    session.add(new_user)
                    session.commit()
                    session.refresh(new_user)
                    print(
                        f"   ✓ 用户 '{username}' 创建成功 (ID: {new_user.id}, 角色：{role})"
                    )
        except Exception as e:
            print(f"   ✗ 创建失败：{e}")

    # 2. 创建测试 Token（关联到用户）
    print("\n2. 创建测试 Token...")
    test_tokens = [
        ("admin_token_123", "admin", 10000),  # 管理员 token
        ("user1_token_456", "user1", 500),  # 普通用户 token
        ("user2_token_789", "user2", 100),  # 限额用户 token
        ("demo_token_000", None, 200),  # 无主 token
    ]

    for token_str, owner_username, remaining in test_tokens:
        try:
            owner_id = None
            if owner_username:
                with Session(db.engine) as session:
                    statement = select(User).where(User.username == owner_username)
                    owner = session.exec(statement).first()
                    if owner:
                        owner_id = owner.id

            # 检查 token 是否已存在
            existing_token = db.read_one_by_condition(
                ApiKey, ApiKey.owner_id == owner_id, ApiKey.token == token_str
            )
            if existing_token:
                print(f"   ⚠ Token '{token_str}' 已存在，跳过")
            else:
                token_info = db.create(
                    ApiKey(
                        token=token_str,
                        owner_id=owner_id,
                        remaining_queries=remaining,
                    )
                )
                print(
                    f"   ✓ Token '{token_str}' 创建成功 (剩余次数：{token_info.remaining_queries}, 所有者：{owner_username or '无'})"
                )
        except Exception as e:
            print(f"   ✗ 创建失败：{e}")

    # 3. 创建题目分类...
    print("\n3. 创建题目分类...")
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
            cat = db.create(Category(name=name, description=description))
            category_ids.append(cat.id)
            print(f"   ✓ 分类 '{name}' 创建成功 (ID: {cat.id})")
        except Exception as e:
            print(f"   ✗ 创建失败：{e}")

    # 4. 添加示例题目（包含新字段）
    print("\n4. 添加示例题目到题库...")
    sample_questions = [
        {
            "question_title": "中国梦的本质是什么？",
            "answer_text": "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "马克思主义活的灵魂是？",
            "answer_text": "具体问题具体分析",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "我国根本的政治制度是？",
            "answer_text": "人民代表大会制度",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "抗日战争爆发于哪一年？",
            "answer_text": "1937 年",
            "category_id": 1,
            "is_ai_generated": False,
            "source": "历史文化题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "光在真空中的传播速度是多少？",
            "answer_text": "约 3×10^8 米/秒（299,792,458 米/秒）",
            "category_id": 2,
            "is_ai_generated": False,
            "source": "科学技术题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "我国的最高国家权力机关是？",
            "answer_text": "全国人民代表大会",
            "category_id": 3,
            "is_ai_generated": False,
            "source": "法律法规题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "新发展理念包括哪些内容？",
            "answer_text": "创新、协调、绿色、开放、共享",
            "category_id": 4,
            "is_ai_generated": False,
            "source": "经济社会题库",
            "question_type": QuestionType.MULTIPLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "教育的根本任务是？",
            "answer_text": "立德树人",
            "category_id": 5,
            "is_ai_generated": False,
            "source": "教育心理题库",
            "question_type": QuestionType.SINGLE,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        # 新增带选项的选择题
        {
            "question_title": "下列哪项不是马克思主义的基本原理？",
            "answer_text": "A",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库",
            "question_type": QuestionType.SINGLE,
            "question_options": "A. 辩证唯物主义\nB. 历史唯物主义\nC. 唯心主义\nD. 科学社会主义",
            "review_status": ReviewStatus.APPROVED,
        },
        {
            "question_title": "以下哪些属于新发展理念？（多选）",
            "answer_text": "A,B,C,D,E",
            "category_id": 4,
            "is_ai_generated": False,
            "source": "经济社会题库",
            "question_type": QuestionType.MULTIPLE,
            "question_options": "A. 创新\nB. 协调\nC. 绿色\nD. 开放\nE. 共享\nF. 合作",
            "review_status": ReviewStatus.APPROVED,
        },
        # 判断题
        {
            "question_title": "中国共产党的初心和使命是为中国人民谋幸福，为中华民族谋复兴。",
            "answer_text": "正确",
            "category_id": 0,
            "is_ai_generated": False,
            "source": "政治理论题库",
            "question_type": QuestionType.JUDGEMENT,
            "question_options": None,
            "review_status": ReviewStatus.APPROVED,
        },
        # 填空题
        {
            "question_title": "我国共有____个少数民族。",
            "answer_text": "55",
            "category_id": 1,
            "is_ai_generated": False,
            "source": "历史文化题库",
            "question_type": QuestionType.COMPLETION,
            "question_options": None,
            "review_status": ReviewStatus.PENDING,
        },
    ]

    question_objects = []
    question_ids = []
    for i, q in enumerate(sample_questions):
        try:
            # 创建题目对象
            question_obj = Question(
                question_title=q["question_title"],
                answer_text=q["answer_text"],
                question_type=q["question_type"],
                question_options=q.get("question_options"),
                is_ai_generated=q["is_ai_generated"],
                source=q["source"],
                review_status=q["review_status"],
            )

            # 保存到数据库
            created_question = db.create(question_obj)
            question_objects.append(created_question)
            question_ids.append(created_question.id)

            # 分配到对应分类
            if q["category_id"] < len(category_ids):
                db.create(
                    QuestionCategory(
                        question_id=created_question.id,
                        category_id=category_ids[q["category_id"]],
                    )
                )

            print(
                f"   ✓ 题目 '{q['question_title'][:20]}...' 添加成功 (ID: {created_question.id}, 类型：{q['question_type'].value})"
            )
        except Exception as e:
            print(f"   ✗ 添加失败：{e}")

    # 5. 添加到向量库（使用新的 VectorStore API）
    print("\n5. 将题目添加到向量库...")
    try:
        # 创建全局向量库实例（category_id=0 表示不分类别）
        vector_store = VectorStore(category_id=0, category_name="全部题目")

        # 批量添加所有题目到向量库
        internal_ids = vector_store.add_documents(question_objects)

        print(f"   ✓ 成功向量化 {len(internal_ids)} 道题目")
        print(f"   ✓ 向量库内部 ID 范围：{min(internal_ids)} - {max(internal_ids)}")

        # 显示统计信息
        vector_store.save_index()
        stats = vector_store.get_stats()
        print(
            f"   ✓ 向量库统计：{stats['total_documents']} 道题目，索引大小：{stats['index_size']}"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"   ✗ 向量化失败：{e}")

    # 6. 记录日志
    print("\n" + "=" * 60)
    print("测试数据初始化完成！")
    print("=" * 60)
    print(f"\n统计信息:")
    print(f"  - 用户数量：{len(test_users)}")
    print(f"  - Token 数量：{len(test_tokens)}")
    print(f"  - 分类数量：{len(categories)}")
    print(f"  - 题目数量：{len(sample_questions)}")
    print(f"  - 向量化题目数：{len(question_ids)}")
    print(f"\n测试用户:")
    for username, password, _, role in test_users:
        print(f"  - {username}/{password} (角色：{role})")
    print(f"\n测试 Token:")
    for token_str, owner, _ in test_tokens:
        print(f"  - {token_str} (所有者：{owner or '无'})")
    print("\n提示：可以使用这些 Token 调用 API 进行测试")
    print("=" * 60)


if __name__ == "__main__":
    init_test_data()
