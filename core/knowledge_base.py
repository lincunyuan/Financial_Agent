# RAG知识库（Milvus+MySQL交互）
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import mysql.connector
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import os
from utils.embedding_utils import EmbeddingGenerator


class FinancialKnowledgeBase:
    def __init__(self, milvus_host: str = "localhost", milvus_port: int = 19530,
                 mysql_host: str = "localhost", mysql_user: str = "root",
                 mysql_password: str = "", mysql_db: str = "financial_rag",
                 embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """初始化向量库和关系型数据库连接"""
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 初始化Milvus连接
                connections.connect(host=milvus_host, port=milvus_port)
                
                # 设置Hugging Face镜像源，解决下载超时问题
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                
                # 使用EmbeddingGenerator类加载模型
                self.embedding_model = EmbeddingGenerator(embedding_model_name)
                self.embedding_model = self.embedding_model.model  # 保留原始SentenceTransformer模型接口

                # 初始化MySQL连接
                self.mysql_conn = mysql.connector.connect(
                    host=mysql_host,
                    user=mysql_user,
                    password=mysql_password,
                    database=mysql_db
                )
                self.create_tables()
                self._init_milvus_collection()
                return
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    import logging
                    logging.warning(f"知识库初始化失败 (重试 {retry_count}/{max_retries}): {e}")
                    time.sleep(2)  # 等待2秒后重试
                else:
                    import logging
                    logging.error(f"知识库初始化失败 (已重试 {max_retries}次): {e}")
                    raise

    def _init_milvus_collection(self):
        """初始化Milvus集合"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding_vector", dtype=DataType.FLOAT_VECTOR, dim=384)
        ]

        schema = CollectionSchema(fields, "Financial document embeddings collection")
        self.collection = Collection("financial_embeddings", schema)

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",
            "params": {"nlist": 1024}
        }
        self.collection.create_index("embedding_vector", index_params)

    def create_tables(self) -> None:
        """创建MySQL数据表"""
        cursor = self.mysql_conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_articles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            source VARCHAR(100),
            publish_time DATETIME,
            url VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.mysql_conn.commit()

    def crawl_financial_news(self, url: str) -> Dict:
        """爬取财经新闻内容"""
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 示例：根据实际网站结构调整选择器
        title = soup.select_one('h1').text.strip() if soup.select_one('h1') else "无标题"
        content = '\n'.join([p.text.strip() for p in soup.select('div.article-content p')])

        return {
            "title": title,
            "content": content,
            "url": url,
            "source": url.split('/')[2],
            "publish_time": None  # 可根据实际网站添加时间提取逻辑
        }

    def add_document_to_kb(self, document: Dict) -> None:
        """将文档添加到知识库（MySQL+Milvus）"""
        # 存储到MySQL
        cursor = self.mysql_conn.cursor()
        insert_query = """
        INSERT INTO financial_articles (title, content, source, url, publish_time)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            document['title'],
            document['content'],
            document['source'],
            document['url'],
            document.get('publish_time')
        ))
        self.mysql_conn.commit()
        doc_id = cursor.lastrowid

        # 生成向量并存储到Milvus
        chunks = self.split_into_chunks(document['content'])
        for chunk in chunks:
            embedding = self.embedding_model.encode(chunk).tolist()
            self.insert_into_milvus(doc_id, chunk, embedding)

    def split_into_chunks(self, text: str, chunk_size: int = 300) -> List[str]:
        """将文档分割为适合向量化的片段"""
        words = text.split()
        return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    def insert_into_milvus(self, doc_id: int, text_chunk: str, embedding: List[float]) -> None:
        """插入文本片段向量到Milvus"""
        data = [
            [doc_id],  # document_id
            [text_chunk],  # text_chunk
            [embedding]  # embedding_vector
        ]
        self.collection.insert(data)
        self.collection.flush()

    def retrieve_relevant_chunks(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索与查询最相关的文本片段"""
        query_embedding = self.embedding_model.encode(query).tolist()

        self.collection.load()

        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding_vector",
            param=search_params,
            limit=top_k,
            output_fields=["document_id", "text_chunk"]
        )

        # 整理检索结果
        relevant_chunks = []
        for hit in results[0]:
            relevant_chunks.append({
                "document_id": hit.entity.get("document_id"),
                "text_chunk": hit.entity.get("text_chunk"),
                "similarity_score": hit.distance
            })

        return relevant_chunks

    def get_url_from_doc_id(self, doc_id: int) -> str:
        """从MySQL获取文档URL"""
        cursor = self.mysql_conn.cursor()
        cursor.execute("SELECT url FROM financial_articles WHERE id = %s", (doc_id,))
        result = cursor.fetchone()
        return result[0] if result else "未知来源"

    def close_connections(self):
        """关闭数据库连接"""
        self.mysql_conn.close()
        connections.disconnect(alias="default")  # 指定默认别名