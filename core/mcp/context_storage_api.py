# MCP核心接口规范 - 上下文存储接口
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod
from datetime import datetime


class ContextStorage(ABC):
    """上下文存储接口规范，支持Redis等存储方式"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取存储引擎名称"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """获取存储引擎版本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查存储引擎是否可用"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """连接到存储引擎"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开与存储引擎的连接"""
        pass


class SessionStorage(ContextStorage):
    """会话存储接口规范，定义对话状态结构"""
    
    @abstractmethod
    def store_conversation(self, user_id: str, user_query: str, bot_response: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """存储单轮对话
        
        Args:
            user_id: 用户ID
            user_query: 用户查询
            bot_response: 机器人响应
            metadata: 对话元数据
            
        Returns:
            bool: 存储结果
        """
        pass
    
    @abstractmethod
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取历史对话记录
        
        Args:
            user_id: 用户ID
            limit: 返回对话轮数
            
        Returns:
            List[Dict]: 对话历史列表，每条记录包含：
                {
                    'query': str,  # 用户查询
                    'response': str,  # 机器人响应
                    'timestamp': str,  # 对话时间戳
                    'metadata': Dict[str, Any]  # 对话元数据
                }
        """
        pass
    
    @abstractmethod
    def update_session_state(self, user_id: str, session_state: Dict[str, Any]) -> bool:
        """更新会话状态
        
        Args:
            user_id: 用户ID
            session_state: 会话状态数据，格式如下：
                {
                    'user_id': str,  # 用户ID
                    'current_stock': {  # 当前关注股票
                        'code': str,  # 股票代码
                        'name': str  # 股票名称
                    },
                    'history': List[Dict],  # 对话历史
                    'pending_entities': Dict[str, Any],  # 待处理实体
                    'last_active_time': str,  # 最后活跃时间
                    'preferences': Dict[str, Any]  # 用户偏好
                }
            
        Returns:
            bool: 更新结果
        """
        pass
    
    @abstractmethod
    def get_session_state(self, user_id: str) -> Dict[str, Any]:
        """获取会话状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 会话状态数据，格式同 update_session_state
        """
        pass
    
    @abstractmethod
    def clear_conversation(self, user_id: str) -> bool:
        """清除用户对话历史
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 清除结果
        """
        pass
    
    @abstractmethod
    def set_pending_entities(self, user_id: str, entities: Dict[str, Any]) -> bool:
        """设置待处理实体
        
        Args:
            user_id: 用户ID
            entities: 待处理实体字典
            
        Returns:
            bool: 设置结果
        """
        pass
    
    @abstractmethod
    def get_pending_entities(self, user_id: str) -> Dict[str, Any]:
        """获取待处理实体
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 待处理实体字典
        """
        pass
    
    @abstractmethod
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """更新用户偏好
        
        Args:
            user_id: 用户ID
            preferences: 用户偏好字典
            
        Returns:
            bool: 更新结果
        """
        pass
    
    @abstractmethod
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户偏好字典
        """
        pass


class CacheStorage(ContextStorage):
    """缓存存储接口规范"""
    
    @abstractmethod
    def set_cache(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒）
            
        Returns:
            bool: 设置结果
        """
        pass
    
    @abstractmethod
    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存值
        """
        pass
    
    @abstractmethod
    def delete_cache(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 删除结果
        """
        pass
    
    @abstractmethod
    def clear_cache(self, pattern: str) -> bool:
        """清除匹配模式的缓存
        
        Args:
            pattern: 匹配模式
            
        Returns:
            bool: 清除结果
        """
        pass


class RedisSessionStorage(SessionStorage):
    """Redis会话存储接口实现规范"""
    
    @abstractmethod
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, max_history_rounds: int = 5):
        """初始化Redis会话存储
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: Redis数据库
            password: Redis密码
            max_history_rounds: 最大历史对话轮数
        """
        pass
    
    @abstractmethod
    def set_expire(self, user_id: str, expire_seconds: int) -> bool:
        """设置会话过期时间
        
        Args:
            user_id: 用户ID
            expire_seconds: 过期时间（秒）
            
        Returns:
            bool: 设置结果
        """
        pass
    
    @abstractmethod
    def get_active_users(self, pattern: str = "*", limit: int = 100) -> List[str]:
        """获取活跃用户列表
        
        Args:
            pattern: 用户ID匹配模式
            limit: 返回用户数量
            
        Returns:
            List[str]: 活跃用户列表
        """
        pass