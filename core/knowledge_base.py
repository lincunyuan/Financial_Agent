# RAG知识库（Milvus+MySQL交互）
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import mysql.connector
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import os
from utils.embedding_utils import EmbeddingGenerator


class FinancialKnowledgeBase:
    def __init__(self, milvus_host: str = None, milvus_port: int = None,
                 mysql_host: str = None, mysql_user: str = None,
                 mysql_password: str = None, mysql_db: str = None,
                 embedding_model_name: str = "qwen3-embedding",
                 collection_name: str = "financial_reportsqwen_fixed"):
        """初始化向量库和关系型数据库连接"""
        import time
        import yaml
        import os
        max_retries = 3
        retry_count = 0
        
        # 读取配置文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "database.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 使用配置文件中的参数，如果没有则使用默认值
        milvus_config = config.get("milvus", {})
        mysql_config = config.get("mysql", {})
        
        milvus_host = milvus_host or milvus_config.get("host", "localhost")
        milvus_port = milvus_port or milvus_config.get("port", 19530)
        mysql_host = mysql_host or mysql_config.get("host", "localhost")
        mysql_user = mysql_user or mysql_config.get("user", "root")
        mysql_password = mysql_password or mysql_config.get("password", "")
        mysql_db = mysql_db or mysql_config.get("database", "financial_rag")
        
        # 尝试启动MySQL服务
        try:
            import subprocess
            import ctypes
            import logging
            
            logger = logging.getLogger(__name__)
            
            # 检查是否以管理员权限运行
            def is_admin():
                try:
                    return ctypes.windll.shell32.IsUserAnAdmin() != 0
                except:
                    return False
            
            # 如果不是管理员权限，尝试以管理员权限启动MySQL服务
            if not is_admin():
                logger.info("尝试以管理员权限启动MySQL服务...")
                # 使用PowerShell以管理员权限启动MySQL服务
                ps_command = "net start MySQL9.5"
                subprocess.run([
                    "powershell",
                    "-Command",
                    f"Start-Process -Verb RunAs -FilePath 'cmd.exe' -ArgumentList '/c {ps_command}' -Wait"
                ], check=False)
            else:
                # 如果已经是管理员权限，直接启动MySQL服务
                logger.info("以管理员权限直接启动MySQL服务...")
                subprocess.run(["net", "start", "MySQL9.5"], check=False)
                
            # 等待服务启动
            import time
            time.sleep(3)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"启动MySQL服务失败: {e}")
        
        while retry_count < max_retries:
            try:
                # 初始化Milvus连接
                connections.connect(host=milvus_host, port=milvus_port)
                
                # 设置Hugging Face镜像源，解决下载超时问题
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                
                # 使用EmbeddingGenerator类加载模型
                self.embedding_model = EmbeddingGenerator(embedding_model_name)
                self.collection_name = collection_name  # 保存集合名称

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
        import logging
        from pymilvus import utility
        
        # 检查集合是否已存在
        if utility.has_collection(self.collection_name):
            logging.info(f"使用已存在的集合: {self.collection_name}")
            self.collection = Collection(self.collection_name)
            # 检查集合是否包含text_chunk字段
            field_names = [field.name for field in self.collection.schema.fields]
            if "text_chunk" not in field_names:
                logging.warning("集合中缺少text_chunk字段，将无法获取文本内容")
        else:
            # 获取向量维度
            try:
                from utils.embedding_utils import EmbeddingGenerator
                temp_embedder = EmbeddingGenerator(self.embedding_model_name)
                vector_dim = temp_embedder.get_dimension()
            except Exception as e:
                logging.error(f"获取向量维度失败: {e}")
                vector_dim = 1024  # qwen3-embedding的默认维度

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=4000),  # 与process_pdf_to_milvus.py保持一致，增加max_length到4000
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim)
            ]

            schema = CollectionSchema(fields, "Financial document embeddings collection")
            self.collection = Collection(self.collection_name, schema)

            # 创建索引，使用HNSW算法优化检索速度
            index_params = {
                "index_type": "HNSW",
                "metric_type": "IP",
                "params": {"M": 16, "efConstruction": 200}
            }
            self.collection.create_index("vector", index_params)
            logging.info(f"创建新集合和索引完成: {self.collection_name}")

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
        import logging
        logger = logging.getLogger(__name__)
        
        # 记录查询的Milvus集合
        logger.info(f"开始检索，使用Milvus集合: {self.collection_name}")
        logger.info(f"查询内容: {query}")
        
        # 使用EmbeddingGenerator的encode方法生成查询向量
        query_embedding = self.embedding_model.encode(query).tolist()
        logger.info(f"生成查询向量，维度: {len(query_embedding)}")

        self.collection.load()
        logger.info(f"已加载集合: {self.collection_name}")

        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        logger.info(f"搜索参数: {search_params}")
        
        # 获取集合的字段列表，确定可以输出哪些字段
        field_names = [field.name for field in self.collection.schema.fields]
        output_fields = ["id"]
        logger.info(f"集合字段列表: {field_names}")
        
        # 如果集合包含text_chunk字段，将其添加到输出字段
        if "text_chunk" in field_names:
            output_fields.append("text_chunk")
        logger.info(f"输出字段: {output_fields}")
        
        # 如果集合包含source和page字段，也将其添加到输出字段
        if "source" in field_names:
            output_fields.append("source")
        if "page" in field_names:
            output_fields.append("page")
        
        logger.info(f"开始Milvus搜索，top_k: {top_k}")
        results = self.collection.search(
            data=[query_embedding],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=output_fields
        )
        
        logger.info(f"搜索完成，返回结果数量: {len(results[0])}")

        # 整理检索结果，包含来源信息
        relevant_chunks = []
        for i, hit in enumerate(results[0]):
            chunk_id = hit.entity.get("id")
            similarity_score = hit.distance
            
            logger.info(f"结果 {i+1}: ID={chunk_id}, 相似度={similarity_score:.4f}")
            
            # 构建结果字典
            result_dict = {
                "id": chunk_id,
                "similarity_score": similarity_score,
                "source": f"Milvus集合: {self.collection_name}"
            }
            
            # 如果有text_chunk字段，添加到结果中
            if "text_chunk" in field_names:
                text_chunk = hit.entity.get("text_chunk")
                result_dict["text_chunk"] = text_chunk
                logger.info(f"  文本片段: {text_chunk[:100]}..." if len(text_chunk) > 100 else f"  文本片段: {text_chunk}")
            
            # 如果有source字段，使用实际的来源信息
            if "source" in field_names:
                source = hit.entity.get("source")
                if source:
                    result_dict["source"] = source
                    logger.info(f"  来源: {source}")
            
            # 如果有page字段，添加页面信息
            if "page" in field_names:
                page = hit.entity.get("page")
                result_dict["page"] = page
                logger.info(f"  页码: {page}")
            
            relevant_chunks.append(result_dict)
        
        logger.info(f"检索完成，共返回 {len(relevant_chunks)} 个相关片段")
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