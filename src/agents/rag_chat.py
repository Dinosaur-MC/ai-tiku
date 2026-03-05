from typing import List, Dict, Optional, Generator
from llm import chat, completion
from db import db, VectorStore
import logging

logger = logging.getLogger(__name__)


class RAGChatAgent:
    """基于检索增强生成（RAG）的对话 Agent"""
    
    def __init__(self, top_k: int = 3):
        """
        初始化 RAG Chat Agent
        
        Args:
            top_k: 检索的相似文档数量
        """
        self.top_k = top_k
        self.vector_store = VectorStore(category_id=0)
        self.chat_history = []  # 对话历史
    
    def chat(self, query: str, use_history: bool = True) -> Dict:
        """
        进行对话式问答
        
        Args:
            query: 用户问题
            use_history: 是否使用对话历史
        
        Returns:
            包含回答和上下文的字典
        """
        # 1. 检索相关文档
        retrieved_docs = self.vector_store.similarity_search(query, k=self.top_k)
        
        if not retrieved_docs:
            # 如果没有检索到内容，直接使用 LLM 回答
            response = self._direct_answer(query, use_history)
            return {
                'answer': response,
                'sources': [],
                'used_retrieval': False
            }
        
        # 2. 构建上下文
        context = self._build_context(retrieved_docs)
        
        # 3. 基于上下文生成回答
        response = self._rag_answer(query, context, use_history)
        
        # 4. 更新对话历史
        if use_history:
            self.chat_history.append({
                'role': 'user',
                'content': query
            })
            self.chat_history.append({
                'role': 'assistant',
                'content': response
            })
        
        # 5. 返回结果
        return {
            'answer': response,
            'sources': [doc['content'] for doc in retrieved_docs],
            'metadata': [doc.get('metadata', {}) for doc in retrieved_docs],
            'used_retrieval': True
        }
    
    def _build_context(self, docs: List[Dict]) -> str:
        """构建上下文文本"""
        context_parts = ["以下是相关的背景信息：\n"]
        
        for i, doc in enumerate(docs, 1):
            content = doc['content']
            answer = doc.get('metadata', {}).get('answer', '')
            
            context_parts.append(f"\n[资料{i}]\n")
            context_parts.append(f"题目：{content}\n")
            if answer:
                context_parts.append(f"答案：{answer}\n")
        
        return "".join(context_parts)
    
    def _rag_answer(self, query: str, context: str, use_history: bool) -> str:
        """基于 RAG 生成回答"""
        messages = self._build_messages(query, context, use_history)
        
        response = chat.invoke(messages)
        return response.content.strip()
    
    def _direct_answer(self, query: str, use_history: bool) -> str:
        """直接回答（不使用检索）"""
        messages = self._build_messages(query, None, use_history)
        
        response = chat.invoke(messages)
        return response.content.strip()
    
    def _build_messages(self, query: str, context: str = None, 
                       use_history: bool = True) -> List[Dict]:
        """构建对话消息列表"""
        messages = []
        
        # 系统提示词
        system_prompt = "你是一个专业的题库助手，负责根据提供的资料回答用户的问题。"
        
        if context:
            system_prompt += "\n请严格基于以下资料回答问题，如果资料中没有相关信息，请告知用户。\n"
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "system", "content": context})
        else:
            system_prompt += "\n如果不知道答案，请诚实地告诉用户。"
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史对话
        if use_history and self.chat_history:
            # 只保留最近 5 轮对话
            recent_history = self.chat_history[-10:]
            messages.extend(recent_history)
        
        # 添加当前问题
        messages.append({"role": "user", "content": query})
        
        return messages
    
    def clear_history(self):
        """清空对话历史"""
        self.chat_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.chat_history.copy()
    
    def add_document(self, question: str, answer: str, metadata: Dict = None):
        """
        添加文档到向量库
        
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
        logger.info(f"已添加文档到向量库：{question[:50]}...")
    
    def batch_add_documents(self, qa_pairs: List[Dict]):
        """
        批量添加文档到向量库
        
        Args:
            qa_pairs: 问答对列表，每个包含 question 和 answer
        """
        documents = []
        metadatas = []
        
        for qa in qa_pairs:
            documents.append(qa['question'])
            metadatas.append({
                'answer': qa.get('answer', ''),
                **qa.get('metadata', {})
            })
        
        self.vector_store.add_documents(
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"已批量添加 {len(documents)} 个文档到向量库")
    
    async def stream_chat(self, query: str, use_history: bool = True):
        """
        流式对话（异步生成器）
        
        Args:
            query: 用户问题
            use_history: 是否使用对话历史
        
        Yields:
            回答文本片段
        """
        # 先检索相关文档
        retrieved_docs = self.vector_store.similarity_search(query, k=self.top_k)
        
        if not retrieved_docs:
            # 直接流式回答
            context = None
        else:
            context = self._build_context(retrieved_docs)
        
        # 构建消息
        messages = self._build_messages(query, context, use_history)
        
        # 流式生成
        full_response = ""
        for chunk in chat.stream(messages):
            if hasattr(chunk, 'content'):
                yield chunk.content
                full_response += chunk.content
        
        # 更新历史
        if use_history:
            self.chat_history.append({
                'role': 'user',
                'content': query
            })
            self.chat_history.append({
                'role': 'assistant',
                'content': full_response
            })


# 单例模式
rag_chat = RAGChatAgent(top_k=3)
