# 向量处理工具# 向量处理工具
import numpy as np
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import torch
import os
from utils.logging import default_logger


class EmbeddingGenerator:
    """文本向量化生成器"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化Embedding模型
        
        Args:
            model_name: 预训练模型名称，支持中英文
                - 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2' (推荐，支持中英文)
                - 'sentence-transformers/all-MiniLM-L6-v2' (英文)
        """
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                local_model_path = "./models/all-MiniLM-L6-v2"
                
                # 优先尝试本地加载
                if os.path.exists(local_model_path):
                    default_logger.info("检测到本地模型，优先加载...")
                    self.model = SentenceTransformer(local_model_path, device="cpu")
                else:
                    # 本地不存在，从网络下载
                    default_logger.info("本地模型不存在，从网络下载...")
                    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                    self.model = SentenceTransformer(model_name, device="cpu")
                    
                    # 下载后保存到本地
                    self.model.save(local_model_path)
                    default_logger.info(f"模型已保存到本地: {local_model_path}")
                
                self.dimension = self.model.get_sentence_embedding_dimension()
                default_logger.info(f"Embedding模型加载成功，维度: {self.dimension}")
                return
                
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    default_logger.warning(f"Embedding模型加载失败 (重试 {retry_count}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    default_logger.error(f"Embedding模型加载失败 (已重试 {max_retries}次): {e}")
                    raise
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            batch_size: 批处理大小
            normalize: 是否归一化向量
            show_progress: 是否显示进度条
        
        Returns:
            向量数组，shape为 (n, dimension) 或 (dimension,)
        """
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress
            )
            
            if single_text:
                return embeddings[0]
            return embeddings
        except Exception as e:
            default_logger.error(f"文本编码失败: {e}")
            raise
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension