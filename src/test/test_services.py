"""
测试服务模块重构

验证新的服务模块是否正常工作
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent  # 指向 src 目录
sys.path.insert(0, str(src_path))

from services.vector_search import vector_search, VectorSearch
from services.ai_responder import ai_responder, AIResponder
from answer_retriever import retriever


def test_vector_search():
    """测试向量搜索服务"""
    print("=" * 50)
    print("测试向量搜索服务")
    print("=" * 50)

    # 测试单例模式
    assert vector_search is not None
    assert isinstance(vector_search, VectorSearch)
    print(f"✓ vector_search 单例已创建：{vector_search}")

    # 测试实例化
    vs = VectorSearch(category_id=0)
    assert vs is not None
    print(f"✓ VectorSearch 实例已创建：{vs}")

    print("\n向量搜索服务测试通过！\n")


def test_ai_responder():
    """测试 AI响应服务"""
    print("=" * 50)
    print("测试 AI响应服务")
    print("=" * 50)

    # 测试单例模式
    assert ai_responder is not None
    assert isinstance(ai_responder, AIResponder)
    print(f"✓ ai_responder 单例已创建：{ai_responder}")

    # 测试实例化
    air = AIResponder()
    assert air is not None
    print(f"✓ AIResponder 实例已创建：{air}")

    # 测试提示词构建
    prompt = air._build_query_prompt(
        "什么是人工智能？",
        options=["A. 机器学习", "B. 深度学习"],
        question_type="single",
    )
    assert "什么是人工智能？" in prompt
    assert "单选题" in prompt
    print(f"✓ 提示词构建正常")

    print("\nAI响应服务测试通过！\n")


def test_answer_retriever():
    """测试答案检索器"""
    print("=" * 50)
    print("测试答案检索器")
    print("=" * 50)

    # 测试单例模式
    assert retriever is not None
    print(f"✓ retriever 单例已创建：{retriever}")

    # 测试 search 方法存在
    assert hasattr(retriever, "search")
    assert hasattr(retriever, "add_to_vectorstore")
    print(f"✓ AnswerRetriever 方法完整")

    print("\n答案检索器测试通过！\n")


def main():
    """运行所有测试"""
    print("\n开始测试服务模块重构...\n")

    try:
        test_vector_search()
        test_ai_responder()
        test_answer_retriever()

        print("=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
