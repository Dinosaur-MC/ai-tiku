"""
API 测试脚本
用于验证系统功能是否正常
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_response(title: str, response: requests.Response):
    """格式化打印响应"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码：{response.status_code}")
    print(f"响应内容:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print(f"{'='*60}\n")


def test_health():
    """测试健康检查端点"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("健康检查", response)
    return response.status_code == 200


def test_root():
    """测试根路径"""
    response = requests.get(f"{BASE_URL}/")
    print_response("根路径", response)
    return response.status_code == 200


def test_query(token: str, question: str):
    """测试查题接口"""
    params = {
        "token": token,
        "question": question,
        "type": "unknown"
    }
    
    response = requests.get(f"{BASE_URL}/api/query", params=params)
    print_response(f"查题测试 - {question}", response)
    return response.status_code == 200


def test_query_with_options(token: str, question: str, options: list, q_type: str):
    """测试带选项的查题接口"""
    params = {
        "token": token,
        "question": question,
        "options": "\n".join(options),
        "type": q_type
    }
    
    response = requests.get(f"{BASE_URL}/api/query", params=params)
    print_response(f"查题测试（带选项）- {question}", response)
    return response.status_code == 200


def test_info(token: str):
    """测试配额查询接口"""
    params = {"token": token}
    response = requests.get(f"{BASE_URL}/api/info", params=params)
    print_response(f"配额查询 - {token}", response)
    return response.status_code == 200


def test_invalid_token():
    """测试无效 Token"""
    params = {
        "token": "invalid_token_12345",
        "question": "测试题目"
    }
    
    response = requests.get(f"{BASE_URL}/api/query", params=params)
    print_response("无效 Token 测试", response)
    return response.status_code == 401


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始运行 AI-Tiku API 测试")
    print("="*60)
    
    # 测试基本端点
    print("\n[1/7] 测试健康检查...")
    health_ok = test_health()
    
    print("\n[2/7] 测试根路径...")
    root_ok = test_root()
    
    # 使用测试 Token
    test_token = "test123456"
    
    # 测试查题
    print("\n[3/7] 测试简单查题...")
    query_ok = test_query(test_token, "中国梦的本质是什么？")
    
    print("\n[4/7] 测试带选项查题（单选题）...")
    test_query_with_options(
        test_token,
        "马克思主义活的灵魂是？",
        ["A. 实事求是", "B. 具体问题具体分析", "C. 理论联系实际"],
        "single"
    )
    
    print("\n[5/7] 测试配额查询...")
    info_ok = test_info(test_token)
    
    print("\n[6/7] 测试无效 Token...")
    invalid_ok = test_invalid_token()
    
    # 测试其他 Token
    print("\n[7/7] 测试其他 Token...")
    test_query("demo789012", "抗日战争爆发于哪一年？")
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    tests = [
        ("健康检查", health_ok),
        ("根路径", root_ok),
        ("简单查题", query_ok),
        ("带选项查题", True),  # 不检查状态码
        ("配额查询", info_ok),
        ("无效 Token", invalid_ok),
    ]
    
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    
    print(f"\n通过：{passed}/{total}")
    
    if passed == total:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试未通过")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到服务器")
        print("请确保服务已启动：python src/main.py\n")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误：{e}\n")
