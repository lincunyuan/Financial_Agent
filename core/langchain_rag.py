# LangChain RAG模块 - 检索增强生成
from pymilvus import connections, Collection, utility
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_classic.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import logging
import numpy as np
import yaml

# 设置日志
logger = logging.getLogger(__name__)

class LocalEmbeddings(BaseModel, Embeddings):
    """
    本地嵌入模型实现，避免网络依赖
    """
    embedding_dim: int = 1536  # 改为1536维，兼容现有配置
    model: Optional[Any] = None  # 声明model字段
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 使用简单的基于哈希的嵌入（完全离线）
        logger.info(f"使用本地嵌入模型，维度: {self.embedding_dim}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """生成文本的嵌入向量"""
        # 简单的基于哈希的嵌入实现
        import hashlib
        import numpy as np
        
        # 使用哈希函数生成固定长度的向量
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        
        # 将哈希字节转换为浮点数向量
        float_vector = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4]
            float_val = np.frombuffer(chunk, dtype=np.float32)[0]
            float_vector.append(float(float_val))
        
        # 调整向量长度到指定维度
        if len(float_vector) > self.embedding_dim:
            float_vector = float_vector[:self.embedding_dim]
        elif len(float_vector) < self.embedding_dim:
            # 补零
            float_vector.extend([0.0] * (self.embedding_dim - len(float_vector)))
        
        return float_vector
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        return [self._get_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        return self._get_embedding(text)

class FinancialRAG:
    """金融领域检索增强生成模块"""
    
    def __init__(self, vector_db_dir: str = None, llm=None, embeddings=None, api_key: str = None, base_url: str = None):
        """初始化RAG模块
        
        Args:
            vector_db_dir: 向量库目录（兼容旧接口，不再使用）
            llm: 语言模型（可以是原始OpenAI客户端或LangChain的LLM对象）
            embeddings: 嵌入模型（兼容旧接口，不再使用）
            api_key: API密钥
            base_url: API基础URL
        """
        # 读取数据库配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "database.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        milvus_config = config.get("milvus", {})
        self.milvus_host = milvus_config.get("host", "localhost")
        self.milvus_port = milvus_config.get("port", 19530)
        self.collection_name = milvus_config.get("collection_name", "financial_reportsqwen_fixed_test_2")  # 从配置文件读取集合名称
        
        # 不再使用的变量，保留仅为兼容旧接口
        self.vector_db_dir = vector_db_dir
        self.embeddings = embeddings
        
        # 初始化Milvus相关变量
        self.collection = None
        self.prompt_template = None
        
        # 初始化嵌入模型
        try:
            from utils.embedding_utils import EmbeddingGenerator
            self.embedding_model = EmbeddingGenerator("qwen3-embedding")
            logger.info("成功初始化嵌入模型")
        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {e}")
            self.embedding_model = None
        
        # 如果是原始OpenAI客户端，或需要重新包装成LangChain的ChatOpenAI
        if llm and (hasattr(llm, 'chat') and hasattr(llm, 'completions')):
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
            # 连接到Milvus
            connections.connect(host=self.milvus_host, port=self.milvus_port)
            logger.info(f"成功连接到Milvus服务器: {self.milvus_host}:{self.milvus_port}")
            
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"成功加载Milvus集合: {self.collection_name}")
            else:
                logger.warning(f"Milvus集合不存在: {self.collection_name}")
                return
            
            # 加载集合到内存
            self.collection.load()
            logger.info(f"已加载集合到内存: {self.collection_name}")
            
            # 存储集合信息
            self.vector_store = "milvus"  # 标记使用Milvus
            
        except Exception as e:
            logger.error(f"初始化Milvus向量存储失败: {e}")
            self.vector_store = None
            self.collection = None
    
    def _init_qa_chain(self):
        """初始化QA链"""
        if not self.llm:
            logger.error("语言模型未初始化，无法创建QA链")
            return
        
        try:
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
            
            # 直接创建QA链，不依赖向量存储的retriever
            self.prompt_template = prompt_template
            logger.info("成功创建RAG QA链")
            
        except Exception as e:
            logger.error(f"初始化QA链失败: {e}")
            self.prompt_template = None
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索与查询相关的文档
        
        Args:
            query: 查询文本
            top_k: 返回前k个最相关的文档
            
        Returns:
            List[Dict]: 相关文档列表
        """
        if not self.collection or not self.embedding_model:
            logger.error("Milvus集合或嵌入模型未初始化，无法检索")
            return []
        
        try:
            logger.info(f"开始检索，查询内容: {query}")
            logger.info(f"使用Milvus集合: {self.collection_name}")
            logger.info(f"检索参数: top_k={top_k}")
            
            # 生成查询向量
            query_embedding = self.embedding_model.encode(query).tolist()
            logger.info(f"生成查询向量，维度: {len(query_embedding)}")
            
            # 搜索参数
            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            
            # 获取集合的字段列表
            field_names = [field.name for field in self.collection.schema.fields]
            output_fields = ["id"]
            
            # 如果集合包含text_chunk字段，将其添加到输出字段
            if "text_chunk" in field_names:
                output_fields.append("text_chunk")
            
            # 如果集合包含source和page字段，也将其添加到输出字段
            if "source" in field_names:
                output_fields.append("source")
            if "page" in field_names:
                output_fields.append("page")
            
            logger.info(f"开始Milvus搜索，输出字段: {output_fields}")
            
            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=output_fields
            )
            
            logger.info(f"搜索完成，返回结果数量: {len(results[0])}")
            
            # 整理检索结果
            retrieved_docs = []
            for i, hit in enumerate(results[0]):
                # 构建结果字典
                doc_info = {
                    "score": hit.distance,
                    "content": hit.entity.get("text_chunk", ""),
                    "metadata": {
                        "source": hit.entity.get("source", f"Milvus集合: {self.collection_name}"),
                        "page": hit.entity.get("page", "")
                    }
                }
                retrieved_docs.append(doc_info)
                
                logger.info(f"检索结果 {i+1}: 相似度={hit.distance:.4f}")
                logger.info(f"  文档内容: {doc_info['content'][:100]}..." if len(doc_info['content']) > 100 else f"  文档内容: {doc_info['content']}")
                logger.info(f"  文档元数据: {doc_info['metadata']}")
            
            logger.info(f"检索完成，共找到 {len(retrieved_docs)} 个相关文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def generate(self, query: str, context: Optional[Dict] = None) -> Dict:
        """生成增强回答
        
        Args:
            query: 查询文本
            context: 额外上下文信息，包含检索到的文档
            
        Returns:
            Dict: 包含回答和来源的字典
        """
        if not self.llm or not self.prompt_template:
            logger.error("语言模型或提示模板未初始化，无法生成回答")
            return {
                "answer": "系统错误：无法生成回答",
                "source_documents": [],
                "success": False
            }
        
        try:
            # 从context中获取检索到的文档
            retrieved_docs = context.get("retrieved_docs", []) if context else []
            
            # 构建上下文文本
            context_text = ""
            for i, doc in enumerate(retrieved_docs):
                context_text += f"来源 {i+1}: {doc['content']}\n"
            
            # 格式化提示词
            formatted_prompt = self.prompt_template.format(
                context=context_text,
                question=query
            )
            
            # 执行生成
            result = self.llm.invoke(formatted_prompt)
            
            # 整理结果
            answer = result.content if hasattr(result, 'content') else str(result)
            source_documents = []
            
            for doc in retrieved_docs:
                source_documents.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"]
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
        """检索并生成增强回答
        
        Args:
            query: 查询文本
            top_k: 返回前k个最相关的文档
            
        Returns:
            Dict: 包含回答和来源的字典
        """
        try:
            logger.info(f"开始RAG流程，查询内容: {query}")
            logger.info(f"RAG配置: Milvus集合={self.collection_name}, top_k={top_k}")
            
            # 先检索相关文档
            logger.info("第一步：执行文档检索")
            retrieved_docs = self.retrieve(query, top_k)
            
            if not retrieved_docs:
                logger.info(f"未检索到相关文档，将使用普通生成模式")
                return {
                    "answer": "",
                    "source_documents": [],
                    "success": True
                }
            
            logger.info("第二步：执行增强生成")
            logger.info(f"将使用 {len(retrieved_docs)} 个检索到的文档作为上下文")
            
            # 使用生成方法获取增强回答，传递检索到的文档作为上下文
            generate_result = self.generate(query, context={"retrieved_docs": retrieved_docs})
            
            logger.info("RAG流程完成")
            logger.info(f"生成结果: 成功={generate_result.get('success', False)}")
            logger.info(f"回答内容: {generate_result.get('answer', '')[:100]}..." if len(generate_result.get('answer', '')) > 100 else f"回答内容: {generate_result.get('answer', '')}")
            
            if generate_result.get('source_documents'):
                logger.info(f"使用的源文档数量: {len(generate_result['source_documents'])}")
                for i, doc in enumerate(generate_result['source_documents'][:3]):  # 只显示前3个源文档
                    logger.info(f"  源文档 {i+1}: {doc['content'][:50]}...")
            
            return generate_result
            
        except Exception as e:
            logger.error(f"RAG流程失败: {e}")
            return {
                "answer": "",
                "source_documents": [],
                "success": False
            }