"""
题目分类 Agent - 基于 LangChain/LangGraph + Pydantic 实现
负责自动将题目分类到合适的类别
注意：此 Agent 仅负责 AI 分类逻辑，不直接访问数据库和 service 层
"""
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import logging

from utils.llm import chat
from agents.prompts.classify import build_classification_prompt

logger = logging.getLogger(__name__)


class ClassificationResult(BaseModel):
    """分类结果模型"""
    category_id: int = Field(description="分类 ID")
    confidence: float = Field(description="置信度，0.0-1.0")
    reason: str = Field(description="分类理由")


class ClassificationState(BaseModel):
    """分类状态模型"""
    question: str
    options: Optional[List[str]] = None
    categories: List[Dict] = []
    category_results: List[ClassificationResult] = []


class ClassificationAgent:
    """题目分类 Agent - 基于 LangGraph 实现"""
    
    def __init__(self):
        """初始化分类 Agent"""
        self.available_categories = []
        # 初始化 Pydantic 输出解析器
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        self._build_graph()
        logger.info("ClassificationAgent 初始化完成，Pydantic 解析器已初始化")
    
    def set_categories(self, categories: List[Dict]):
        """
        设置可用分类列表（由外部传入）
        
        Args:
            categories: 分类列表，每个包含 id, name, description
        """
        self.available_categories = categories
        logger.debug(f"已设置 {len(self.available_categories)} 个分类")
    
    def _build_graph(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(ClassificationState)
        
        # 添加节点
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("parse_results", self._parse_results_node)
        
        # 设置入口点
        workflow.set_entry_point("classify")
        
        # 添加边
        workflow.add_edge("classify", "parse_results")
        workflow.add_edge("parse_results", END)
        
        # 编译工作流
        self.graph = workflow.compile()
        logger.debug("LangGraph 工作流已构建")
    
    def _classify_node(self, state: ClassificationState) -> Dict:
        """分类节点（使用LangChain Pydantic 输出解析）"""
        logger.debug(f"开始分类：question='{state['question'][:50]}...'")
        
        if not self.available_categories:
            logger.warning("没有可用分类，返回空结果")
            return {'category_results': []}
        
        # 构建提示词
        prompt = build_classification_prompt(
            self.available_categories,
            state['question'],
            state['options']
        )
        
        # 添加格式指令
        format_instructions = self.parser.get_format_instructions()
        full_prompt = f"{prompt}\n\n请严格按照以下 JSON Schema 格式返回:\n{format_instructions}"
        
        messages = [
            SystemMessage(content="你是一个专业的题库分类助手，负责根据题目内容将其分类到合适的类别。"),
            HumanMessage(content=full_prompt)
        ]
        
        logger.info("调用 LLM 进行分类...")
        response = chat.invoke(messages)
        logger.debug(f"LLM 返回原始内容：'{response.content[:100]}...'")
        
        try:
            # 使用 Pydantic 解析器自动解析
            classification_result = self.parser.parse(response.content)
            logger.info(f"分类解析成功：category_id={classification_result.category_id}")
            return {'category_results': [classification_result]}
        except Exception as e:
            logger.error(f"分类解析失败：{str(e)}，使用默认分类")
            # 解析失败时使用默认分类
            return {
                'category_results': [{
                    'category_id': self.available_categories[0]['id'],
                    'confidence': 0.5,
                    'reason': '解析失败，使用默认分类'
                }]
            }
    
    def _parse_results_node(self, state: ClassificationState) -> Dict:
        """解析分类结果节点（已在上游完成，直接返回）"""
        # 由于已经在 classify_node 中使用 Pydantic 解析，这里直接返回
        if isinstance(state['category_results'], list):
            logger.debug("已经是列表格式")
            return {'category_results': state['category_results']}
        elif hasattr(state['category_results'], 'dict'):
            # 如果是单个 Pydantic 对象
            return {'category_results': [state['category_results']]}
        else:
            logger.warning("未知格式，返回空列表")
            return {'category_results': []}
    
    def classify(self, question_text: str, options: List[str] = None) -> List[Dict]:
        """
        对题目进行分类
        
        Args:
            question_text: 题目文本
            options: 选项列表
            
        Returns:
            分类结果列表
        """
        logger.info(f"收到分类请求：question='{question_text[:50]}...'")
        
        initial_state = {
            'question': question_text,
            'options': options,
            'categories': self.available_categories,
            'category_results': []
        }
        
        result = self.graph.invoke(initial_state)
        logger.info(f"分类完成，返回 {len(result['category_results'])} 个结果")
        
        return result['category_results']


# 单例模式
classifier = ClassificationAgent()
logger.info("ClassificationAgent 单例已创建")
