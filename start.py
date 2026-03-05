#!/usr/bin/env python3
"""
快速启动脚本
用于一键初始化并启动 AI-Tiku 服务
"""

import subprocess
import sys
from pathlib import Path


def print_banner(text: str):
    """打印横幅"""
    width = 60
    print("=" * width)
    print(f"{text:^{width}}")
    print("=" * width)


def check_ollama():
    """检查 Ollama 是否运行"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ Ollama 服务正在运行")
            return True
        else:
            print("✗ Ollama 服务未运行")
            return False
    except Exception as e:
        print(f"✗ 无法连接到 Ollama: {e}")
        return False


def init_database():
    """初始化数据库"""
    print_banner("初始化数据库")
    
    script_path = Path(__file__).parent / "src/init_db.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent,
            timeout=60
        )
        
        if result.returncode == 0:
            print("\n✓ 数据库初始化完成\n")
            return True
        else:
            print(f"\n✗ 数据库初始化失败\n")
            return False
    except Exception as e:
        print(f"\n✗ 数据库初始化出错：{e}\n")
        return False


def start_server():
    """启动服务器"""
    print_banner("启动 AI-Tiku 服务")
    
    script_path = Path(__file__).parent / "src/main.py"
    try:
        print("正在启动 FastAPI 服务器...")
        print("访问地址：http://localhost:8000")
        print("API 文档：http://localhost:8000/docs")
        print("按 Ctrl+C 停止服务\n")
        
        subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent
        )
    except KeyboardInterrupt:
        print("\n\n✓ 服务已停止")
    except Exception as e:
        print(f"\n✗ 服务启动失败：{e}")


def main():
    """主函数"""
    print_banner("AI-Tiku 快速启动")
    
    # 检查 Ollama
    print("\n[1/3] 检查 Ollama 服务...")
    if not check_ollama():
        print("\n⚠️  警告：Ollama 未运行，请先启动 Ollama 服务")
        print("   运行命令：ollama serve")
        choice = input("\n是否继续？(y/N): ").strip().lower()
        if choice != 'y':
            print("已取消启动")
            return
    
    # 初始化数据库（仅首次）
    data_dir = Path(__file__).parent / "data"
    db_file = data_dir / "db.sqlite3"
    
    if not db_file.exists():
        print("\n[2/3] 首次运行，需要初始化数据库...")
        if not init_database():
            print("初始化失败，退出")
            return
    else:
        print("\n[2/3] 数据库已存在，跳过初始化")
    
    # 启动服务
    print("\n[3/3] 启动 Web 服务...")
    start_server()


if __name__ == "__main__":
    main()
