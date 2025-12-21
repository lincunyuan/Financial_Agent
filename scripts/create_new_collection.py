#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建新的Milvus集合，使用指定的模型维度
"""

import logging
import sys
import os

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('create_new_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_new_collection():
    """创建新的Milvus集合"""
    try:
        # 导入必要的模块
        from utils.config_loader import default_config_loader
        from pymilvus import MilvusClient
        
        # 加载配置
        config_loader = default_config_loader
        db_config = config_loader.load_config("database.yaml")
        
        # 连接Milvus服务器
        milvus_uri = f"http://{db_config['milvus']['host']}:{db_config['milvus']['port']}"
        milvus_client = MilvusClient(uri=milvus_uri)
        logger.info(f"成功连接到Milvus服务: {milvus_uri}")
        
        # 新集合名称
        new_collection_name = "financial_reportsqwen"
        
        # 检查集合是否已存在
        if milvus_client.has_collection(collection_name=new_collection_name):
            logger.warning(f"集合 {new_collection_name} 已存在")
            return False
        
        # 加载qwen3-embedding模型以获取维度
        from utils.embedding_utils import EmbeddingGenerator
        embedding_model = EmbeddingGenerator("qwen3-embedding")
        embedding_dim = embedding_model.get_dimension()
        logger.info(f"模型维度: {embedding_dim}")
        
        # 创建新集合
        milvus_client.create_collection(
            collection_name=new_collection_name,
            dimension=embedding_dim,
            primary_field_name="id",
            vector_field_name="vector",
            metric_type="IP"  # 内积相似度
        )
        
        logger.info(f"成功创建新集合: {new_collection_name}，向量维度: {embedding_dim}")
        return True
        
    except Exception as e:
        logger.error(f"创建集合失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("开始创建新的Milvus集合")
    success = create_new_collection()
    if success:
        logger.info("集合创建成功！")
    else:
        logger.error("集合创建失败！")
    sys.exit(0 if success else 1)
