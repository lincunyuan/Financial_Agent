# 向量处理工具
import numpy as np
from typing import List, Union, Optional
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
                - 'qwen3-embedding' (中文，阿里云开发的Embedding模型)
        """
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 检查是否是qwen3-embedding模型
                if model_name == "qwen3-embedding":
                    from transformers import AutoModel, AutoTokenizer
                    
                    # 为qwen3-embedding创建本地模型路径
                    local_model_path = "./models/Qwen3-Embedding-0.6B/Qwen/Qwen3-Embedding-0___6B"
                    
                    # 优先尝试本地加载
                    if os.path.exists(local_model_path):
                        default_logger.info("检测到本地qwen3-embedding模型，优先加载...")
                        self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)
                        self.model = AutoModel.from_pretrained(local_model_path)
                    else:
                        # 本地不存在，从网络下载
                        default_logger.info("本地qwen3-embedding模型不存在，从网络下载...")
                        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B")
                        self.model = AutoModel.from_pretrained("Qwen/Qwen3-Embedding-0.6B")
                        
                        # 下载后保存到本地
                        self.tokenizer.save_pretrained(local_model_path)
                        self.model.save_pretrained(local_model_path)
                        default_logger.info(f"qwen3-embedding模型已保存到本地: {local_model_path}")
                    
                    # Qwen3-embedding模型的向量维度
                    self.dimension = 1024
                    self.model_type = "qwen3"
                else:
                    # 使用sentence-transformers模型
                    from sentence_transformers import SentenceTransformer
                    
                    # 为不同的sentence-transformers模型创建不同的本地路径
                    local_model_path = f"./models/{model_name.split('/')[-1]}"
                    
                    # 优先尝试本地加载
                    if os.path.exists(local_model_path):
                        default_logger.info("检测到本地sentence-transformers模型，优先加载...")
                        self.model = SentenceTransformer(local_model_path, device="cpu")
                    else:
                        # 本地不存在，从网络下载
                        default_logger.info("本地sentence-transformers模型不存在，从网络下载...")
                        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                        self.model = SentenceTransformer(model_name, device="cpu")
                        
                        # 下载后保存到本地
                        self.model.save(local_model_path)
                        default_logger.info(f"sentence-transformers模型已保存到本地: {local_model_path}")
                    
                    self.dimension = self.model.get_sentence_embedding_dimension()
                    self.model_type = "sentence_transformers"
                
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
        # 检查输入是否为空
        if isinstance(texts, str):
            if not texts.strip():
                # 返回零向量
                return np.zeros(self.dimension)
            texts = [texts]
            single_text = True
        else:
            # 过滤空文本
            texts = [text.strip() for text in texts if text.strip()]
            single_text = False
        
        try:
            # 如果所有文本都为空，返回零向量数组
            if not texts:
                if single_text:
                    return np.zeros(self.dimension)
                else:
                    return np.array([])
            
            if hasattr(self, 'model_type') and self.model_type == "qwen3":
                # 使用qwen3-embedding模型进行编码
                embeddings = []
                
                for text in texts:
                    # 对文本进行标记化
                    inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
                    
                    # 模型推理获取隐藏状态
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                    
                    # 获取最后一层的隐藏状态
                    last_hidden = outputs.last_hidden_state
                    
                    # 使用CLS标记的表示作为嵌入
                    cls_embedding = last_hidden[:, 0, :].squeeze().numpy()
                    embeddings.append(cls_embedding)
                
                embeddings = np.array(embeddings)
            else:
                # 使用sentence-transformers模型进行编码
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress
                )
            
            # 归一化向量
            if normalize and len(embeddings) > 0:
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            
            if single_text:
                return embeddings[0]
            return embeddings
        except Exception as e:
            default_logger.error(f"文本编码失败: {e}")
            raise
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension