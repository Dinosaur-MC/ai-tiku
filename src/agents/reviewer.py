from typing import Dict, Optional, List
from llm import completion
import json


class ReviewerAgent:
    """答案复审 Agent - 审核和修正 AI 生成的答案"""
    
    def __init__(self):
        self.review_history = []
    
    def review(self, question: str, answer: str, 
               options: List[str] = None, 
               question_type: str = "unknown",
               corrections: str = None) -> Dict:
        """
        复审答案
        
        Args:
            question: 题目内容
            answer: 待复审的答案
            options: 选项列表（可选）
            question_type: 题目类型
            corrections: 用户提供的修正建议（可选）
        
        Returns:
            复审结果，包含：
            - is_correct: 是否正确
            - confidence: 置信度
            - corrected_answer: 修正后的答案（如果有）
            - explanation: 解释说明
            - suggestions: 改进建议
        """
        # 构建复审提示词
        prompt = self._build_review_prompt(
            question, answer, options, question_type, corrections
        )
        
        # 调用 LLM 进行复审
        response = completion.invoke(prompt)
        result = self._parse_review_response(response.content.strip())
        
        # 记录复审历史
        self.review_history.append({
            'question': question,
            'original_answer': answer,
            'review_result': result
        })
        
        return result
    
    def _build_review_prompt(self, question: str, answer: str,
                            options: List[str] = None,
                            question_type: str = "unknown",
                            corrections: str = None) -> str:
        """构建复审提示词"""
        prompt_parts = [
            "请作为专业的答题审核员，对以下题目的答案进行复审。\n\n",
            "题目：\n",
            question,
            "\n\n"
        ]
        
        if options:
            prompt_parts.append("选项：\n")
            for i, opt in enumerate(options):
                prompt_parts.append(f"{chr(65 + i)}. {opt}\n")
            prompt_parts.append("\n")
        
        if question_type != "unknown":
            type_map = {
                "single": "单选题",
                "multiple": "多选题",
                "judgement": "判断题",
                "completion": "填空题",
                "unknown": "未知题型"
            }
            prompt_parts.append(f"题型：{type_map.get(question_type, '未知题型')}\n\n")
        
        prompt_parts.append("待复审的答案：\n")
        prompt_parts.append(answer)
        prompt_parts.append("\n\n")
        
        if corrections:
            prompt_parts.append("用户修正建议：\n")
            prompt_parts.append(corrections)
            prompt_parts.append("\n\n")
        
        prompt_parts.append(
            "请从以下维度进行审核：\n"
            "1. 答案是否准确回答了问题\n"
            "2. 答案是否与选项匹配（如果有选项）\n"
            "3. 答案是否存在事实性错误\n"
            "4. 答案的表述是否清晰、简洁\n\n"
            "请返回 JSON 格式的审核结果：\n"
            "{\n"
            '  "is_correct": true/false,\n'
            '  "confidence": 0.0-1.0,\n'
            '  "corrected_answer": "修正后的答案（如有必要）",\n'
            '  "explanation": "审核说明",\n'
            '  "suggestions": ["改进建议 1", "改进建议 2"]\n'
            "}\n"
        )
        
        return "".join(prompt_parts)
    
    def _parse_review_response(self, response_text: str) -> Dict:
        """解析 LLM 返回的复审结果"""
        try:
            # 尝试直接解析 JSON
            result = json.loads(response_text)
            
            # 确保必要的字段存在
            if 'is_correct' not in result:
                result['is_correct'] = True
            if 'confidence' not in result:
                result['confidence'] = 0.8
            if 'explanation' not in result:
                result['explanation'] = "审核通过"
            if 'suggestions' not in result:
                result['suggestions'] = []
            
            return result
            
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return result
                except json.JSONDecodeError:
                    pass
            
            # 如果都失败，返回默认结果
            return {
                'is_correct': True,
                'confidence': 0.5,
                'corrected_answer': None,
                'explanation': '无法解析审核结果，默认通过',
                'suggestions': []
            }
    
    def batch_review(self, qa_pairs: List[Dict]) -> List[Dict]:
        """
        批量复审答案
        
        Args:
            qa_pairs: 问答对列表，每个包含 question 和 answer
        
        Returns:
            复审结果列表
        """
        results = []
        for qa in qa_pairs:
            result = self.review(
                question=qa['question'],
                answer=qa['answer'],
                options=qa.get('options'),
                question_type=qa.get('type', 'unknown')
            )
            results.append(result)
        return results
    
    def get_review_statistics(self) -> Dict:
        """获取复审统计信息"""
        if not self.review_history:
            return {
                'total_reviews': 0,
                'correct_rate': 0.0,
                'average_confidence': 0.0
            }
        
        total = len(self.review_history)
        correct_count = sum(
            1 for r in self.review_history 
            if r['review_result'].get('is_correct', False)
        )
        avg_confidence = sum(
            r['review_result'].get('confidence', 0.0)
            for r in self.review_history
        ) / total
        
        return {
            'total_reviews': total,
            'correct_rate': correct_count / total,
            'average_confidence': avg_confidence
        }


# 单例模式
reviewer = ReviewerAgent()
