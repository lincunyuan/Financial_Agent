#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Milvus集合的向量维度
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_loader import default_config_loader
from pymilvus import MilvusClient

# 加载配置
db_config = default_config_loader.load_config("database.yaml")
milvus_uri = f"http://{db_config['milvus']['host']}:{db_config['milvus']['port']}"

# 连接到Milvus
client = MilvusClient(uri=milvus_uri)

# 检查集合信息
collection_name = "financial_reports"
if client.has_collection(collection_name=collection_name):
    collection_info = client.describe_collection(collection_name=collection_name)
    print(f"集合 '{collection_name}' 信息:")
    print(f"  向量维度: {collection_info['properties']['dimension']}")
    print(f"  向量字段名: {collection_info['properties']['vector_field_name']}")
    print(f"  主键字段名: {collection_info['properties']['primary_field_name']}")
    print(f"  相似度度量: {collection_info['properties']['metric_type']}")
else:
    print(f"集合 '{collection_name}' 不存在")

# 列出所有集合
all_collections = client.list_collections()
print(f"\n所有Milvus集合: {all_collections}")
