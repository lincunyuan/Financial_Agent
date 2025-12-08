# LLM客户端（支持OpenAI API和本地模型）
import os
import yaml
from typing import Optional, Dict, List
from utils.logging import default_logger


class LLMClient:
    """LLM客户端，支持多种大模型接口"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化LLM客户端
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.provider = self.config.get("provider", "openai")
        self._init_client()
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        if config_path is None:
            # 使用绝对路径加载配置文件，确保在任何目录下都能找到
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "model_config.yaml")
        elif not os.path.isabs(config_path):
            # 如果提供的是相对路径，转换为绝对路径
            config_path = os.path.abspath(config_path)
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                default_logger.info(f"成功加载LLM配置: {config_path}")
                return config
            else:
                default_logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return {}
        except Exception as e:
            default_logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _init_client(self):
        """根据配置初始化客户端"""
        if self.provider == "openai":
            self._init_openai_client()
        elif self.provider == "local":
            self._init_local_client()
        else:
            default_logger.warning(f"未知的LLM提供商: {self.provider}，将使用模拟模式")
            self.client = None
    
    def _init_openai_client(self):
        """初始化OpenAI客户端（支持OpenAI和兼容模型如qwen-plus）"""
        try:
            import openai
            api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                default_logger.warning("未找到API Key，将使用模拟模式")
                self.client = None
                return
            
            # 获取base_url配置（支持OpenAI和兼容模型如qwen-plus）
            base_url = self.config.get("base_url")
            
            # 如果是qwen系列模型，设置默认的base_url
            self.model_name = self.config.get("model", "gpt-3.5-turbo")
            if self.model_name.startswith("qwen-") and not base_url:
                base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            # 初始化客户端
            if base_url:
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
                default_logger.info(f"OpenAI兼容客户端初始化成功，模型: {self.model_name}, base_url: {base_url}")
            else:
                self.client = openai.OpenAI(api_key=api_key)
                default_logger.info(f"OpenAI客户端初始化成功，模型: {self.model_name}")
        except ImportError:
            default_logger.warning("未安装openai库，将使用模拟模式。请运行: pip install openai")
            self.client = None
        except Exception as e:
            default_logger.error(f"OpenAI客户端初始化失败: {e}，将使用模拟模式")
            self.client = None
    
    def _init_local_client(self):
        """初始化本地模型客户端（示例：Ollama）"""
        try:
            base_url = self.config.get("base_url", "http://localhost:11434")
            self.model_name = self.config.get("model", "llama2")
            self.base_url = base_url
            default_logger.info(f"本地模型客户端初始化成功，URL: {base_url}, 模型: {self.model_name}")
        except Exception as e:
            default_logger.error(f"本地模型客户端初始化失败: {e}，将使用模拟模式")
            self.client = None
    
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        生成回答
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
        
        Returns:
            生成的文本
        """
        if self.client is None:
            return self._mock_generate(prompt)
        
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature)
            elif self.provider == "local":
                return self._generate_local(prompt, max_tokens, temperature)
            else:
                return self._mock_generate(prompt)
        except Exception as e:
            default_logger.error(f"LLM生成失败: {e}")
            return f"[错误] 生成回答时出现问题: {str(e)}"
    
    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """使用OpenAI API生成"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的财经知识助手，能够基于提供的知识库和实时数据回答用户问题。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    def _generate_local(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """使用本地模型生成（Ollama示例）"""
        try:
            import requests
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                default_logger.error(f"本地模型请求失败: {response.status_code}")
                return self._mock_generate(prompt)
        except Exception as e:
            default_logger.error(f"本地模型调用失败: {e}")
            return self._mock_generate(prompt)
    
    def _mock_generate(self, prompt: str) -> str:
        """模拟生成（用于测试或未配置LLM时）"""
        default_logger.warning("使用模拟LLM生成回答")
        return f"""基于您的问题，我将提供一个模拟回答。在实际配置LLM后，这里将显示真实的智能回答。

提示词长度: {len(prompt)} 字符
[注意] 请配置真实的LLM API以获取实际回答。您可以：
1. 配置OpenAI API: 在config/model_config.yaml中设置api_key，或设置环境变量OPENAI_API_KEY
2. 配置本地模型: 在config/model_config.yaml中设置provider为local并配置base_url和model"""
