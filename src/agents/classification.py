from typing import List, Dict, Optional
from llm import completion
from db import db


class ClassificationAgent:
    """题目分类 Agent - 自动将题目分类到合适的类别"""
    
    def __init__(self):
        self.available_categories = []
        self._load_categories()
    
    def _load_categories(self):
        """加载所有可用分类"""
        self.available_categories = db.get_all_categories()
    
    def classify(self, question_text: str, options: List[str] = None) -> List[Dict]:
        """
        对题目进行分类
        
        Args:
            question_text: 题目内容
            options: 选项列表（可选）
        
        Returns:
            分类结果列表，每个包含 category_id 和 confidence
        """
        # 如果没有可用分类，返回空列表
        if not self.available_categories:
            return []
        
        # 构建提示词
        prompt = self._build_classification_prompt(question_text, options)
        
        # 调用 LLM 获取分类建议
        response = completion.invoke(prompt)
        categories = self._parse_llm_response(response.content.strip())
        
        return categories
    
    def _build_classification_prompt(self, question: str, options: List[str] = None) -> str:
        """构建分类提示词"""
        categories_str = "\n".join([
            f"- {cat['id']}: {cat['name']} ({cat['description'] or ''})"
            for cat in self.available_categories
        ])
        
        prompt_parts = [
            "请分析以下题目，并将其分类到最合适的类别中。\n\n",
            "可用类别：\n",
            categories_str,
            "\n\n题目内容：\n",
            question,
            "\n"
        ]
        
        if options:
            prompt_parts.append("\n选项：\n")
            for i, opt in enumerate(options):
                prompt_parts.append(f"{chr(65 + i)}. {opt}\n")
        
        prompt_parts.append(
            "\n请返回分类结果，格式为 JSON 数组，每个元素包含：\n"
            "- category_id: 类别 ID（整数）\n"
            "- confidence: 置信度（0-1 之间的浮点数）\n"
            "- reason: 分类理由（简短说明）\n\n"
            "示例输出：\n"
            '[{"category_id": 1, "confidence": 0.95, "reason": "题目涉及基础概念"}]\n'
        )
        
        return "".join(prompt_parts)
    
    def _parse_llm_response(self, response_text: str) -> List[Dict]:
        """解析 LLM 返回的分类结果"""
        import json
        
        try:
            # 尝试直接解析 JSON
            result = json.loads(response_text)
            if isinstance(result, list):
                return result
            
            # 如果是单个对象，转为列表
            if isinstance(result, dict):
                return [result]
            
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    if isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    pass
        
        # 如果都失败，返回默认分类（第一个类别）
        if self.available_categories:
            return [{
                'category_id': self.available_categories[0]['id'],
                'confidence': 0.5,
                'reason': '默认分类'
            }]
        
        return []
    
    def add_category(self, name: str, description: str = None) -> int:
        """
        添加新分类
        
        Args:
            name: 分类名称
            description: 分类描述
        
        Returns:
            新分类的 ID
        """
        category_id = db.create_category(name, description)
        self._load_categories()  # 重新加载分类
        return category_id
    
    def assign_to_question(self, question_id: int, category_ids: List[int]):
        """
        将题目分配到多个分类
        
        Args:
            question_id: 题目 ID
            category_ids: 分类 ID 列表
        """
        for cat_id in category_ids:
            db.assign_category(question_id, cat_id)
    
    def get_categories_for_question(self, question_id: int) -> List[Dict]:
        """
        获取题目的所有分类
        
        Args:
            question_id: 题目 ID
        
        Returns:
            分类信息列表
        """
        # TODO: 需要从数据库查询题目关联的分类
        # 这里暂时返回空列表
        return []


# 单例模式
classifier = ClassificationAgent()
