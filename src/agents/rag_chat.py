from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import logging

from utils.llm import chat
from utils.dbc import VectorStore

logger = logging.getLogger(__name__)


class RAGChatState(BaseModel):
    """RAG 对话状态模型"""
    query: str
    use_history: bool = True
    context: Optional[str] = None
    sources: List[str] = []
    metadata: List[Dict] = []
    answer: str = ""
    used_retrieval: bool = False


class RAGChatAgent:
    """RAG 对话 Agent - 基于 LangGraph 实现"""
    
    def __init__(self, top_k: int = 3):
        """
        初始化 RAG Chat Agent
        
        Args:
            top_k: 检索的相似文档数量
        """
        self.top_k = top_k
        self.vector_store = VectorStore(category_id=0)
        self.chat_history = []
        self._build_graph()
        logger.info(f"RAGChatAgent 初始化完成，top_k={top_k}")
    
    def _build_graph(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(RAGChatState)
        
        # 添加节点
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        
        # 设置入口点
        workflow.set_entry_point("retrieve")
        
        # 添加边
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        # 编译工作流
        self.graph = workflow.compile()
        logger.debug("LangGraph 工作流已构建")
    
    def _retrieve_node(self, state: RAGChatState) -> Dict:
        """检索节点"""
        query = state['query']
        logger.debug(f"开始检索：query='{query[:50]}...'")
        
        # 检索相关文档
        retrieved_docs = self.vector_store.similarity_search(query, k=self.top_k)
        
        if not retrieved_docs:
            logger.warning("未检索到相关文档")
            return {
                'context': None,
                'sources': [],
                'metadata': [],
                'used_retrieval': False
            }
        
        logger.info(f"检索到 {len(retrieved_docs)} 个相关文档")
        
        # 构建上下文
        context = self._build_context(retrieved_docs)
        sources = [doc['content'] for doc in retrieved_docs]
        metadata = [doc.get('metadata', {}) for doc in retrieved_docs]
        
        logger.debug(f"上下文长度：{len(context)} 字符")
        return {
            'context': context,
            'sources': sources,
            'metadata': metadata,
            'used_retrieval': True
        }
    
    def _generate_node(self, state: RAGChatState) -> Dict:
        """生成答案节点"""
        logger.debug(f"开始生成回答：query='{state['query'][:50]}...'")
        
        messages = self._build_messages(
            state['query'],
            state['context'],
            state['use_history']
        )
        
        logger.info("调用 LLM 生成回答...")
        response = chat.invoke(messages)
        answer = response.content.strip()
        logger.info(f"LLM 返回回答：'{answer[:100]}...'")
        
        return {'answer': answer}
    
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
        
        context = "".join(context_parts)
        logger.debug(f"构建上下文，共 {len(docs)} 个资料，{len(context)} 字符")
        return context
    
    def _build_messages(self, query: str, context: str = None, 
                       use_history: bool = True) -> List:
        """构建对话消息"""
        messages = []
        
        # 系统提示词
        system_prompt = "你是一个专业的题库助手，负责根据提供的资料回答用户的问题。"
        
        if context:
            system_prompt += "\n请严格基于以下资料回答问题，如果资料中没有相关信息，请告知用户。\n"
            messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=context))
            logger.debug("使用上下文模式")
        else:
            system_prompt += "\n如果不知道答案，请诚实地告诉用户。"
            messages.append(SystemMessage(content=system_prompt))
            logger.debug("直接回答模式")
        
        # 添加历史对话
        if use_history and self.chat_history:
            recent_history = self.chat_history[-10:]
            for msg in recent_history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(SystemMessage(content=msg['content']))
            logger.debug(f"使用历史对话，共 {len(recent_history)} 条")
        
        # 添加当前问题
        messages.append(HumanMessage(content=query))
        logger.debug(f"消息列表构建完成，共 {len(messages)} 条消息")
        
        return messages
    
    def chat(self, query: str, use_history: bool = True) -> Dict:
        """对话式问答"""
        logger.info(f"收到对话请求：query='{query[:50]}...', use_history={use_history}")
        
        initial_state = {
            'query': query,
            'use_history': use_history,
            'context': None,
            'sources': [],
            'metadata': [],
            'answer': '',
            'used_retrieval': False
        }
        
        result = self.graph.invoke(initial_state)
        
        # 更新对话历史
        if use_history:
            self.chat_history.append({
                'role': 'user',
                'content': query
            })
            self.chat_history.append({
                'role': 'assistant',
                'content': result['answer']
            })
            logger.debug(f"对话历史已更新，当前 {len(self.chat_history)} 条")
        
        logger.info(f"对话完成，回答长度：{len(result['answer'])}")
        return {
            'answer': result['answer'],
            'sources': result['sources'],
            'metadata': result['metadata'],
            'used_retrieval': result['used_retrieval']
        }
    
    def clear_history(self):
        """清空对话历史"""
        count = len(self.chat_history)
        self.chat_history = []
        logger.info(f"已清空对话历史，共清除 {count} 条记录")
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.chat_history.copy()
    
    def add_document(self, question: str, answer: str, metadata: Dict = None):
        """添加文档到向量库"""
        doc_metadata = {'answer': answer}
        if metadata:
            doc_metadata.update(metadata)
        
        self.vector_store.add_documents(
            documents=[question],
            metadatas=[doc_metadata]
        )
        logger.info(f"已添加文档到向量库：{question[:50]}...")
    
    def batch_add_documents(self, qa_pairs: List[Dict]):
        """批量添加文档到向量库"""
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


# 单例模式
rag_chat = RAGChatAgent(top_k=3)
logger.info("RAGChatAgent 单例已创建")
