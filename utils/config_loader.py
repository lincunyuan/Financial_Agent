# 配置文件加载工具
import os
import yaml
from typing import Dict, Optional, Any
from pathlib import Path
from utils.logging import default_logger


class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self._configs = {}
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        加载单个配置文件
        
        Args:
            config_file: 配置文件名
        
        Returns:
            配置字典
        """
        if config_file in self._configs:
            return self._configs[config_file]
        
        config_path = self.config_dir / config_file
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                self._configs[config_file] = config
                default_logger.info(f"成功加载配置文件: {config_path}")
                return config
            else:
                default_logger.warning(f"配置文件不存在: {config_path}，返回空配置")
                return {}
        except Exception as e:
            default_logger.error(f"加载配置文件失败 {config_path}: {e}")
            return {}
    
    def get(self, config_file: str, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            config_file: 配置文件名
            key: 配置键（支持点号分隔的嵌套键，如 "database.host"）
            default: 默认值
        
        Returns:
            配置值
        """
        config = self.load_config(config_file)
        
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def load_all_configs(self) -> Dict[str, Dict]:
        """加载所有配置文件"""
        config_files = [
            "api_keys.yaml",
            "database.yaml",
            "model_config.yaml"
        ]
        
        all_configs = {}
        for config_file in config_files:
            all_configs[config_file] = self.load_config(config_file)
        
        return all_configs


# 全局配置加载器实例
default_config_loader = ConfigLoader()
