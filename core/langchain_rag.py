# LangChain RAG模块 - 检索增强生成
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_classic.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, List, Optional
import os
import logging

# 设置日志
logger = logging.getLogger(__name__)

class FinancialRAG:
    """金融领域检索增强生成模块"""
    
    def __init__(self, vector_db_dir: str, llm, embeddings, api_key: str = None, base_url: str = None):
        """初始化RAG模块
        
        Args:
            vector_db_dir: 向量库目录
            llm: 语言模型（可以是原始OpenAI客户端或LangChain的LLM对象）
            embeddings: 嵌入模型
            api_key: API密钥
            base_url: API基础URL
        """
        self.vector_db_dir = vector_db_dir
        self.embeddings = embeddings
        self.vector_store = None
        self.qa_chain = None
        
        # 如果是原始OpenAI客户端，或需要重新包装成LangChain的ChatOpenAI
        if hasattr(llm, 'chat') and hasattr(llm, 'completions'):
            # 根据用户提供的成功示例，使用正确的参数名
            self.llm = ChatOpenAI(
                model="qwen-turbo",  # 使用用户示例中的模型
                openai_api_key=api_key,  # 使用openai_api_key参数
                openai_api_base=base_url,  # 使用openai_api_base参数
                temperature=0  # 使用用户示例中的温度参数
            )
        else:
            # 已经是LangChain的LLM对象
            self.llm = llm
        
        # 初始化向量存储和QA链
        self._init_vector_store()
        self._init_qa_chain()
    
    def _init_vector_store(self):
        """初始化向量存储"""
        try:
            if os.path.exists(self.vector_db_dir):
                self.vector_store = Chroma(
                    persist_directory=self.vector_db_dir,
                    embedding_function=self.embeddings
                )
                logger.info(f"成功加载向量库，路径: {self.vector_db_dir}")
            else:
                logger.warning(f"向量库不存在，路径: {self.vector_db_dir}")
                self.vector_store = Chroma(
                    persist_directory=self.vector_db_dir,
                    embedding_function=self.embeddings
                )
        except Exception as e:
            logger.error(f"初始化向量存储失败: {e}")
            self.vector_store = None
    
    def _init_qa_chain(self):
        """初始化QA链"""
        if not self.vector_store:
            logger.error("向量存储未初始化，无法创建QA链")
            return
        
        try:
            # 创建检索器
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}  # 检索前3个最相关的文档
            )
            
            # 自定义提示模板
            prompt_template = PromptTemplate(
                template="""
                你是一个金融领域的专家，需要基于提供的上下文回答用户的问题。
                
                上下文信息:
                {context}
                
                用户问题:
                {question}
                
                回答要求:
                1. 严格基于提供的上下文信息回答，不要添加额外信息
                2. 如果上下文没有相关信息，回答"根据提供的信息无法回答该问题"
                3. 回答要简洁明了，使用专业的金融术语
                4. 如果有多个相关片段，请综合分析后回答
                
                请开始回答:
                """,
                input_variables=["context", "question"]
            )
            
            # 创建QA链
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt_template}
            )
            
            logger.info("成功创建RAG QA链")
            
        except Exception as e:
            logger.error(f"初始化QA链失败: {e}")
            self.qa_chain = None
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索与查询相关的文档
        
        Args:
            query: 查询文本
            top_k: 返回前k个最相关的文档
            
        Returns:
            List[Dict]: 相关文档列表
        """
        if not self.vector_store:
            logger.error("向量存储未初始化，无法检索")
            return []
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # 整理检索结果
            retrieved_docs = []
            for doc, score in results:
                retrieved_docs.append({
                    "content": doc.page_content,
                    "score": score,
                    "metadata": doc.metadata
                })
            
            logger.info(f"成功检索到 {len(retrieved_docs)} 个相关文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def generate(self, query: str, context: Optional[Dict] = None) -> Dict:
        """生成增强回答
        
        Args:
            query: 查询文本
            context: 额外上下文信息
            
        Returns:
            Dict: 包含回答和来源的字典
        """
        if not self.qa_chain:
            logger.error("QA链未初始化，无法生成回答")
            return {
                "answer": "系统错误：无法生成回答",
                "source_documents": [],
                "success": False
            }
        
        try:
            # 执行QA链
            result = self.qa_chain.invoke({"query": query})
            
            # 整理结果
            answer = result.get("result", "")
            source_documents = []
            
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    source_documents.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    })
            
            logger.info("成功生成RAG增强回答")
            return {
                "answer": answer,
                "source_documents": source_documents,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return {
                "answer": f"生成回答失败：{str(e)}",
                "source_documents": [],
                "success": False
            }
    
    def retrieve_and_generate(self, query: str, top_k: int = 3) -> Dict:
        """检索相关文档并生成增强回答
        
        Args:
            query: 查询文本
            top_k: 检索前k个最相关的文档
            
        Returns:
            Dict: 包含回答、检索到的文档和来源的字典
        """
        # 先检索相关文档
        retrieved_docs = self.retrieve(query, top_k=top_k)
        
        # 然后生成增强回答
        result = self.generate(query)
        
        # 合并结果
        return {
            "answer": result["answer"],
            "retrieved_documents": retrieved_docs,
            "source_documents": result["source_documents"],
            "success": result["success"]
        }
