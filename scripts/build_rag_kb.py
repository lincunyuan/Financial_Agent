#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建金融RAG知识库
使用LangChain的DirectoryLoader加载PDF文件，分块后存储到Chroma向量库
"""

import os
import sys
from typing import List, Optional
from langchain.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
import requests
import logging
import yaml

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_loader import default_config_loader

class QwenEmbeddings(Embeddings):
    """通义千问嵌入模型包装器"""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """初始化嵌入模型
        
        Args:
            api_key: 通义千问API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表
        
        Args:
            texts: 文档文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 批量处理，每次最多处理100个文本
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                payload = {
                    "model": "text-embedding-v1",
                    "input": batch_texts
                }
                
                response = requests.post(f"{self.base_url}/embeddings", headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if "data" in data:
                    batch_embeddings = [item["embedding"] for item in data["data"]]
                    all_embeddings.extend(batch_embeddings)
            
            logger.info(f"成功嵌入 {len(all_embeddings)} 个文档")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"嵌入文档失败: {e}")
            # 如果API调用失败，返回空嵌入
            return [[0.0] * 1536 for _ in texts]  # 假设1536维向量
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本
        
        Args:
            text: 查询文本
            
        Returns:
            List[float]: 嵌入向量
        """
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else [0.0] * 1536

def load_pdf_documents(pdf_dir: str) -> List[Document]:
    """加载PDF文档
    
    Args:
        pdf_dir: PDF文件目录
        
    Returns:
        List[Document]: 文档列表
    """
    try:
        logger.info(f"开始加载PDF文档，目录: {pdf_dir}")
        
        # 使用LangChain的DirectoryLoader和PyPDFLoader
        loader = DirectoryLoader(
            path=pdf_dir,
            glob="*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True,
            use_multithreading=True
        )
        
        documents = loader.load()
        logger.info(f"成功加载 {len(documents)} 个PDF文档")
        
        return documents
        
    except Exception as e:
        logger.error(f"加载PDF文档失败: {e}")
        return []

def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 100) -> List[Document]:
    """对文档进行分块
    
    Args:
        documents: 文档列表
        chunk_size: 块大小
        chunk_overlap: 块重叠大小
        
    Returns:
        List[Document]: 分块后的文档列表
    """
    try:
        logger.info(f"开始分块文档，总文档数: {len(documents)}")
        
        # 使用RecursiveCharacterTextSplitter进行分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", "", ".", "。", "!"]
        )
        
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"成功分块为 {len(split_docs)} 个文档块")
        
        return split_docs
        
    except Exception as e:
        logger.error(f"分块文档失败: {e}")
        return []

def build_vector_store(documents: List[Document], embeddings: Embeddings, persist_dir: str) -> Optional[Chroma]:
    """构建向量存储
    
    Args:
        documents: 文档列表
        embeddings: 嵌入模型
        persist_dir: 向量库持久化目录
        
    Returns:
        Optional[Chroma]: 向量存储实例
    """
    try:
        logger.info(f"开始构建向量存储，文档数: {len(documents)}")
        
        # 创建Chroma向量库
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        
        # 持久化向量库
        vector_store.persist()
        logger.info(f"向量存储构建完成并持久化到: {persist_dir}")
        
        return vector_store
        
    except Exception as e:
        logger.error(f"构建向量存储失败: {e}")
        return None

def build_rag_kb(pdf_dir: str, vector_db_dir: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> bool:
    """构建RAG知识库
    
    Args:
        pdf_dir: PDF文件目录
        vector_db_dir: 向量库目录
        chunk_size: 块大小
        chunk_overlap: 块重叠大小
        
    Returns:
        bool: 是否成功构建
    """
    try:
        logger.info("=== 开始构建金融RAG知识库 ===")
        
        # 1. 加载配置
        config_loader = default_config_loader
        api_keys_config = config_loader.load_config("api_keys.yaml")
        
        # 2. 初始化嵌入模型
        embeddings = QwenEmbeddings(
            api_key=api_keys_config.get("qwen_api_key", ""),
            base_url=api_keys_config.get("qwen_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        
        # 3. 加载PDF文档
        documents = load_pdf_documents(pdf_dir)
        if not documents:
            logger.error("没有加载到任何PDF文档")
            return False
        
        # 4. 分块文档
        split_docs = split_documents(documents, chunk_size, chunk_overlap)
        if not split_docs:
            logger.error("文档分块失败")
            return False
        
        # 5. 构建向量存储
        vector_store = build_vector_store(split_docs, embeddings, vector_db_dir)
        if not vector_store:
            logger.error("向量存储构建失败")
            return False
        
        # 6. 输出统计信息
        logger.info(f"=== 知识库构建完成 ===")
        logger.info(f"原始文档数: {len(documents)}")
        logger.info(f"分块后文档数: {len(split_docs)}")
        logger.info(f"向量库路径: {vector_db_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"构建RAG知识库失败: {e}")
        return False

if __name__ == "__main__":
    """主函数"""
    # 配置路径
    pdf_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pdfs")
    vector_db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db")
    
    # 创建向量库目录
    os.makedirs(vector_db_dir, exist_ok=True)
    
    # 构建知识库
    success = build_rag_kb(pdf_dir, vector_db_dir)
    
    if success:
        logger.info("RAG知识库构建成功！")
        sys.exit(0)
    else:
        logger.error("RAG知识库构建失败！")
        sys.exit(1)
