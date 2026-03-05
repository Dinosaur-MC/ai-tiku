from typing import Optional, List, Dict, Any
from db import db, VectorStore
from llm import completion, embedder
import numpy as np


class AnswerRetriever:
    """答案检索器 - 核心查题逻辑"""
    
    def __init__(self):
        self.vector_store = VectorStore(category_id=0)  # 默认使用全局题库
    
    def search(self, query_text: str, options: List[str] = None, 
               question_type: str = "unknown", more: bool = False, force_ai = False) -> Dict[str, Any]:
        """
        搜索答案
        
        Args:
            query_text: 查询的题目文本
            options: 选项列表（用于 AI 辅助答题）
            question_type: 题目类型 (single, multiple, judgement, completion, unknown)
            more: 是否返回多个结果（已禁用，但保留兼容）
        
        Returns:
            包含答案的字典
        """
        if not force_ai:
            # 1. 首先尝试向量相似度搜索
            similar_results = self.vector_store.similarity_search(query_text, k=5)
            
            if similar_results and not more:
                # 找到相似题目，直接返回
                best_match = similar_results[0]
                return {
                    'found': True,
                    'question': best_match['content'],
                    'answer': best_match.get('metadata', {}).get('answer', ''),
                    'ai': False,
                    'similar_results': similar_results
                }
            
            if similar_results and more:
                # 返回多个结果
                results = []
                for item in similar_results:
                    results.append({
                        'question': item['content'],
                        'answer': item.get('metadata', {}).get('answer', ''),
                        'ai': False
                    })
                return {
                    'found': True,
                    'results': results,
                    'similar_results': similar_results
                }
            
        # 2. 未找到相似题目，使用 LLM 生成答案
        ai_answer = self._generate_ai_answer(
            query_text, options, question_type
        )
        
        if not more:
            return {
                'found': True,
                'question': query_text,
                'answer': ai_answer,
                'ai': True,
                'similar_results': []
            }
        else:
            return {
                'found': True,
                'results': [{
                    'question': query_text,
                    'answer': ai_answer,
                    'ai': True
                }],
                'similar_results': []
            }
    
    def _generate_ai_answer(self, question: str, options: List[str] = None,
                           question_type: str = "unknown") -> str:
        """
        使用 LLM 生成答案
        
        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型
        
        Returns:
            AI 生成的答案
        """
        # 构建提示词
        prompt = self._build_query_prompt(question, options, question_type)
        
        # 调用 LLM
        response = completion.invoke(prompt)
        return response.strip()
    
    def _build_query_prompt(self, question: str, options: List[str] = None,
                           question_type: str = "unknown") -> str:
        """
        构建查询提示词
        
        Args:
            question: 题目内容
            options: 选项列表
            question_type: 题目类型
        
        Returns:
            提示词字符串
        """
        prompt_parts = ["请回答以下问题：\n"]
        prompt_parts.append(f"题目：{question}\n")
        
        if options:
            prompt_parts.append("\n选项：\n")
            for i, opt in enumerate(options):
                prompt_parts.append(f"{chr(65 + i)}. {opt}\n")
        
        if question_type != "unknown":
            type_map = {
                "single": "单选题",
                "multiple": "多选题",
                "judgement": "判断题",
                "completion": "填空题",
                "unknown": "未知题型"
            }
            prompt_parts.append(f"\n题型：{type_map.get(question_type, '未知题型')}\n")
        
        prompt_parts.append("\n请直接给出答案，不需要解释。")
        
        return "".join(prompt_parts)
    
    def add_to_vectorstore(self, question: str, answer: str, 
                          metadata: Dict = None):
        """
        将题目添加到向量库
        
        Args:
            question: 题目内容
            answer: 答案内容
            metadata: 额外元数据
        """
        doc_metadata = {'answer': answer}
        if metadata:
            doc_metadata.update(metadata)
        
        self.vector_store.add_documents(
            documents=[question],
            metadatas=[doc_metadata]
        )


# 单例模式
retriever = AnswerRetriever()
