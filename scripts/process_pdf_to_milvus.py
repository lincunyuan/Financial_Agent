#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理财报PDF并更新Milvus向量数据库的流程

核心环节：
1. PDF解析与文本提取
2. 文本分块与向量化
3. Milvus向量更新
4. 验证与异常处理
"""

import os
import sys
import logging
import random
import re
from typing import List, Dict, Any
import pdfplumber
from FlagEmbedding import BGEM3FlagModel
from pymilvus import MilvusClient

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_pdf_to_milvus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 中文句子分割函数
def split_chinese_sentences(text):
    """用正则表达式分割中文句子（处理句号、感叹号、问号）"""
    sentences = re.split(r'[。！？]', text)
    # 过滤空字符串，保留完整句子
    return [sent.strip() + '。' for sent in sentences if sent.strip()]

class FinancialPDFProcessor:
    """
    财报PDF处理器，实现从PDF解析到Milvus向量更新的完整流程
    """
    def __init__(self, milvus_uri: str = None, 
                 collection_name: str = "financial_reports",
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 use_lite: bool = False):
        """
        初始化处理器
        
        Args:
            milvus_uri: Milvus服务地址或本地文件路径（Milvus Lite）
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
            use_lite: 是否使用Milvus Lite模式
        """
        # 添加项目根目录到Python路径
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 加载配置
        from utils.config_loader import default_config_loader
        self.config_loader = default_config_loader
        db_config = self.config_loader.load_config("database.yaml")
        
        # 使用配置文件中的Milvus连接信息或默认值
        if milvus_uri:
            self.milvus_uri = milvus_uri
        elif use_lite:
            # Milvus Lite模式：使用本地文件路径（使用绝对路径）
            import os
            self.milvus_uri = os.path.abspath("milvus.db")
            logger.info(f"使用Milvus Lite模式，数据将存储在: {self.milvus_uri}")
        else:
            # 默认使用配置文件中的Milvus服务器连接
            self.milvus_uri = f"http://{db_config['milvus']['host']}:{db_config['milvus']['port']}"
        
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # 初始化Milvus客户端
        self.milvus_client = None
        # 初始化嵌入模型
        self.embedding_model_instance = None
        
        self.initialize_components()
    
    def initialize_components(self):
        """初始化Milvus客户端和嵌入模型"""
        try:
            # 初始化Milvus客户端
            self.milvus_client = MilvusClient(uri=self.milvus_uri)
            logger.info(f"成功连接到Milvus服务: {self.milvus_uri}")
            
            # 初始化嵌入模型（必须在创建集合之前初始化，因为创建集合需要模型维度）
            logger.info(f"正在加载嵌入模型: {self.embedding_model}")
            from utils.embedding_utils import EmbeddingGenerator
            self.embedding_model_instance = EmbeddingGenerator(self.embedding_model)
            logger.info("嵌入模型加载完成")
            
            # 检查集合是否存在
            if not self.milvus_client.has_collection(collection_name=self.collection_name):
                logger.warning(f"集合 {self.collection_name} 不存在，将创建新集合")
                self.create_collection()
            
        except Exception as e:
            if "milvus-lite is required" in str(e):
                logger.error("Milvus Lite需要单独安装。请尝试以下命令:")
                logger.error("pip install pymilvus[milvus_lite]")
                logger.error("注意：Milvus Lite目前不支持Python 3.13，请考虑以下解决方案:")
                logger.error("1. 使用Python 3.12或更低版本")
                logger.error("2. 不使用--use-lite参数，改用完整的Milvus服务器（需要先启动Milvus服务）")
                logger.error("3. 运行Docker命令启动Milvus服务器: docker run -d --name milvus-standalone --memory 4g --memory-swap 8g -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.6.7 milvus run standalone")
                logger.error(f"详细错误信息: {e}")
            elif "Fail connecting to server" in str(e):
                logger.error("无法连接到Milvus服务器，请确保:")
                logger.error("1. Milvus服务器已启动并正在运行")
                logger.error("2. 连接地址和端口正确")
                logger.error("3. 防火墙没有阻止连接")
                logger.error("如果您想使用本地模式，请添加--use-lite参数（注意：Python 3.13不支持Milvus Lite）")
                logger.error(f"详细错误信息: {e}")
            else:
                logger.error(f"初始化组件失败: {e}")
            raise
    
    def create_collection(self):
        """创建Milvus集合"""
        try:
            # 获取模型输出维度
            embedding_dim = self.embedding_model_instance.get_dimension()
            
            # 创建集合
            self.milvus_client.create_collection(
                collection_name=self.collection_name,
                dimension=embedding_dim,
                primary_field_name="id",
                vector_field_name="vector",
                metric_type="IP"  # 内积相似度
            )
            logger.info(f"成功创建集合 {self.collection_name}，向量维度: {embedding_dim}")
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        logger.info(f"开始解析PDF文件: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                page_count = len(pdf.pages)
                logger.info(f"PDF文件共 {page_count} 页")
                
                for i, page in enumerate(pdf.pages, 1):
                    logger.debug(f"处理第 {i}/{page_count} 页")
                    
                    # 提取文本
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                    
                    # 提取表格并转换为文本
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            # 将表格转换为文本格式
                            table_text = "\n表格:\n"
                            for row in table:
                                row_text = "\t".join([str(cell) if cell else "" for cell in row])
                                table_text += row_text + "\n"
                            full_text += table_text + "\n"
            
            # 检查提取的文本是否为空
            if not full_text or not full_text.strip():
                logger.warning(f"PDF解析完成，但未提取到任何文本内容。可能是扫描版PDF或加密PDF。")
                logger.warning("建议尝试使用OCR工具（如pytesseract）进行文本提取。")
                return ""
            
            logger.info(f"PDF解析完成，提取文本长度: {len(full_text)} 字符")
            return full_text
        
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")
            # 可以在这里添加OCR备选方案
            raise
    
    def chunk_text(self, text: str, max_tokens: int = 1024) -> List[str]:
        """
        文本分块
        
        Args:
            text: 原始文本
            max_tokens: 每块最大token数
            
        Returns:
            文本块列表
        """
        logger.info(f"开始文本分块，目标每块最大 {max_tokens} tokens")
        
        # 检查输入文本是否为空
        if not text or not text.strip():
            logger.warning("输入文本为空，无法进行有效分块")
            return []
        
        try:
            # 使用正则表达式分割中文句子（替代nltk.sent_tokenize）
            sentences = split_chinese_sentences(text)
            logger.info(f"文本分割为 {len(sentences)} 个句子")
            
            chunks = []
            current_chunk = ""
            current_tokens = 0
            
            for sentence in sentences:
                # 估算token数（按平均每个单词1.3个token计算）
                sentence_tokens = len(sentence.split()) * 1.3
                
                if current_tokens + sentence_tokens > max_tokens and current_chunk:
                    # 当前块已满，保存并开始新块
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
                    current_tokens = sentence_tokens
                else:
                    # 添加到当前块
                    current_chunk += sentence + " "
                    current_tokens += sentence_tokens
            
            # 添加最后一个块
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            logger.info(f"文本分块完成，共 {len(chunks)} 个块")
            if chunks:
                logger.debug(f"块大小统计: 最小 {min(len(chunk.split()) for chunk in chunks)} 词, 最大 {max(len(chunk.split()) for chunk in chunks)} 词")
            
            return chunks
            
        except Exception as e:
            logger.warning(f"使用正则表达式分块失败: {e}，将使用备用分块方法")
            
            # 使用备用分块方法：按段落和字符数分割
            # 先按空行分割成段落
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            chunks = []
            current_chunk = ""
            current_tokens = 0
            
            for paragraph in paragraphs:
                # 估算段落的token数
                paragraph_tokens = len(paragraph.split()) * 1.3
                
                if current_tokens + paragraph_tokens > max_tokens and current_chunk:
                    # 当前块已满，保存并开始新块
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n"
                    current_tokens = paragraph_tokens
                else:
                    # 添加到当前块
                    current_chunk += paragraph + "\n"
                    current_tokens += paragraph_tokens
                
                # 如果单个段落过长，进一步分割
                if len(current_chunk.split()) * 1.3 > max_tokens * 1.5:
                    # 将长块按字符数分割
                    words = current_chunk.split()
                    half_length = len(words) // 2
                    
                    # 分割成两个块
                    first_half = " ".join(words[:half_length])
                    second_half = " ".join(words[half_length:])
                    
                    chunks.append(first_half.strip())
                    current_chunk = second_half.strip() + "\n"
                    current_tokens = len(second_half.split()) * 1.3
            
            # 添加最后一个块
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            logger.info(f"备用分块方法完成，共 {len(chunks)} 个块")
            
            return chunks
    
    def generate_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """
        生成文本块的向量表示
        
        Args:
            text_chunks: 文本块列表
            
        Returns:
            向量列表
        """
        # 检查输入文本块列表是否为空
        filtered_chunks = [chunk for chunk in text_chunks if chunk and chunk.strip()]
        if not filtered_chunks:
            logger.warning("没有可用的非空文本块来生成向量")
            return []
        
        logger.info(f"开始生成向量，共 {len(filtered_chunks)} 个非空文本块")
        
        try:
            # 生成向量
            embeddings = self.embedding_model_instance.encode(filtered_chunks)
            
            # 确保返回的是Python列表格式
            if hasattr(embeddings, 'tolist'):
                embeddings = embeddings.tolist()
            
            logger.info(f"向量生成完成，向量维度: {len(embeddings[0])}")
            return embeddings
            
        except Exception as e:
            logger.error(f"向量生成失败: {e}")
            raise
    
    def update_milvus(self, embeddings: List[List[float]], text_chunks: List[str], 
                     pdf_metadata: Dict[str, Any] = None) -> int:
        """
        更新Milvus向量数据库
        
        Args:
            embeddings: 向量列表
            text_chunks: 文本块列表
            pdf_metadata: PDF元数据
            
        Returns:
            更新的记录数
        """
        logger.info(f"开始更新Milvus数据库，共 {len(embeddings)} 条记录")
        
        try:
            # 准备数据
            data = []
            for i, (vector, text) in enumerate(zip(embeddings, text_chunks)):
                record = {
                    "id": i,  # 使用简单的ID生成策略，实际应用中应使用更唯一的ID
                    "vector": vector,
                    "text": text,
                    "source": pdf_metadata.get("path", "unknown") if pdf_metadata else "unknown",
                    "page": pdf_metadata.get("page", 0) if pdf_metadata else 0
                }
                data.append(record)
            
            # 使用upsert操作更新数据
            result = self.milvus_client.upsert(
                collection_name=self.collection_name,
                data=data
            )
            
            updated_count = result.get("upsert_count", 0)
            logger.info(f"Milvus更新完成，共更新 {updated_count} 条记录")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Milvus更新失败: {e}")
            raise
    
    def process_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        处理单个PDF文件的完整流程
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            处理结果
        """
        logger.info(f"开始处理PDF文件: {pdf_path}")
        
        try:
            # 1. PDF解析与文本提取
            full_text = self.extract_text_from_pdf(pdf_path)
            if not full_text or not full_text.strip():
                logger.warning(f"PDF文件 {pdf_path} 提取的文本为空，无法继续处理")
                return {
                    "success": False,
                    "pdf_path": pdf_path,
                    "error": "PDF文件提取的文本为空"
                }
            
            # 2. 文本分块
            text_chunks = self.chunk_text(full_text)
            if not text_chunks:
                logger.warning(f"PDF文件 {pdf_path} 文本分块失败，无法继续处理")
                return {
                    "success": False,
                    "pdf_path": pdf_path,
                    "error": "PDF文本分块失败"
                }
            
            # 3. 文本向量化
            embeddings = self.generate_embeddings(text_chunks)
            if not embeddings:
                logger.warning(f"PDF文件 {pdf_path} 向量生成失败，无法继续处理")
                return {
                    "success": False,
                    "pdf_path": pdf_path,
                    "error": "PDF文本向量化失败"
                }
            
            # 4. Milvus向量更新
            pdf_metadata = {
                "path": pdf_path,
                "filename": os.path.basename(pdf_path)
            }
            updated_count = self.update_milvus(embeddings, text_chunks, pdf_metadata)
            
            # 5. 验证
            self.verify_update(text_chunks, embeddings)
            
            result = {
                "success": True,
                "pdf_path": pdf_path,
                "text_length": len(full_text),
                "chunks_count": len(text_chunks),
                "updated_count": updated_count
            }
            
            logger.info(f"PDF文件处理完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"处理PDF文件失败: {e}")
            return {
                "success": False,
                "pdf_path": pdf_path,
                "error": str(e)
            }
    
    def verify_update(self, text_chunks: List[str], embeddings: List[List[float]]):
        """
        验证更新结果
        
        Args:
            text_chunks: 文本块列表
            embeddings: 向量列表
        """
        logger.info("开始验证更新结果")
        
        try:
            # 随机抽样验证
            sample_size = min(5, len(text_chunks))
            sample_indices = random.sample(range(len(text_chunks)), sample_size)
            
            for idx in sample_indices:
                text_chunk = text_chunks[idx]
                embedding = embeddings[idx]
                
                # 使用向量查询相似度
                search_result = self.milvus_client.search(
                    collection_name=self.collection_name,
                    data=[embedding],
                    limit=1,
                    output_fields=["text"]
                )
                
                if search_result and search_result[0]:
                    top_result = search_result[0][0]
                    retrieved_text = top_result["entity"]["text"]
                    similarity = top_result["distance"]
                    
                    logger.debug(f"验证样本 {idx}: 相似度={similarity:.4f}")
                    logger.debug(f"原始文本片段: {text_chunk[:100]}...")
                    logger.debug(f"检索文本片段: {retrieved_text[:100]}...")
                    
                    # 检查相似度阈值
                    if similarity < 0.8:
                        logger.warning(f"样本 {idx} 相似度较低: {similarity:.4f}")
            
            logger.info("更新验证完成")
            
        except Exception as e:
            logger.error(f"验证更新失败: {e}")
            # 验证失败不影响主流程，只记录日志
    
    def process_pdf_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        处理目录中的所有PDF文件
        
        Args:
            directory_path: PDF文件目录
            
        Returns:
            处理结果统计
        """
        logger.info(f"开始处理目录中的PDF文件: {directory_path}")
        
        # 查找目录中的所有PDF文件
        pdf_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    pdf_files.append(pdf_path)
        
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 处理每个PDF文件
        results = []
        success_count = 0
        failure_count = 0
        
        for pdf_path in pdf_files:
            result = self.process_single_pdf(pdf_path)
            results.append(result)
            
            if result["success"]:
                success_count += 1
            else:
                failure_count += 1
        
        # 统计结果
        total_chunks = sum(result.get("chunks_count", 0) for result in results if result["success"])
        total_updated = sum(result.get("updated_count", 0) for result in results if result["success"])
        
        summary = {
            "total_files": len(pdf_files),
            "success_files": success_count,
            "failure_files": failure_count,
            "total_chunks": total_chunks,
            "total_updated_records": total_updated,
            "detailed_results": results
        }
        
        logger.info(f"目录处理完成，统计结果: {summary}")
        return summary

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='处理财报PDF并更新Milvus向量数据库')
    parser.add_argument('--pdf-path', type=str, required=True, 
                        help='PDF文件或目录路径')
    parser.add_argument('--milvus-uri', type=str, default=None,
                        help='Milvus服务地址或本地文件路径（Milvus Lite）')
    parser.add_argument('--collection-name', type=str, default='financial_reports',
                        help='Milvus集合名称')
    parser.add_argument('--embedding-model', type=str, default='sentence-transformers/all-MiniLM-L6-v2',
                        help='嵌入模型名称')
    parser.add_argument('--use-lite', action='store_true',
                        help='使用Milvus Lite模式（本地文件存储，无需外部服务）')
    
    args = parser.parse_args()
    
    try:
        # 创建处理器实例
        processor = FinancialPDFProcessor(
            milvus_uri=args.milvus_uri,
            collection_name=args.collection_name,
            embedding_model=args.embedding_model,
            use_lite=args.use_lite
        )
        
        # 处理PDF文件或目录
        if os.path.isfile(args.pdf_path):
            # 处理单个文件
            result = processor.process_single_pdf(args.pdf_path)
        elif os.path.isdir(args.pdf_path):
            # 处理目录
            result = processor.process_pdf_directory(args.pdf_path)
        else:
            raise ValueError(f"路径 {args.pdf_path} 不存在")
        
        # 打印结果
        print("\n处理完成！")
        print(f"成功: {result.get('success', True) if isinstance(result, dict) else 'N/A'}")
        if 'total_files' in result:
            print(f"总文件数: {result['total_files']}")
            print(f"成功文件数: {result['success_files']}")
            print(f"失败文件数: {result['failure_files']}")
            print(f"总文本块数: {result['total_chunks']}")
            print(f"总更新记录数: {result['total_updated_records']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        print(f"\n错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
