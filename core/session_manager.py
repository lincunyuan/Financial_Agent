# Redis会话管理（对话存储与上下文构建）
import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

# 导入MCP核心接口
from core.mcp import RedisSessionStorage

from utils.config_loader import default_config_loader

# 设置日志
logging.basicConfig(level=logging.INFO)


class RedisSessionManager(RedisSessionStorage):
    def __init__(self, host: str = None, port: int = None, db: int = None, password: str = None, max_history_rounds: int = 5, default_ttl: int = 1800):
        """初始化Redis连接"""
        # 从配置文件加载默认配置
        redis_config = default_config_loader.get("database.yaml", "redis", {})
        
        # 使用传入参数或配置文件中的值
        self.host = host or redis_config.get("host", "localhost")
        self.port = port or redis_config.get("port", 6379)
        self.db = db or redis_config.get("db", 0)
        self.password = password or redis_config.get("password")
        self.max_history_rounds = max_history_rounds  # 保留最近对话轮数
        self.default_ttl = default_ttl  # 默认过期时间，单位：秒（1800秒=30分钟）
        
        # 建立Redis连接
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_connect_timeout=5,
            decode_responses=True
        )
    
    def get_name(self) -> str:
        """获取存储引擎名称"""
        return "RedisSessionStorage"
    
    def get_version(self) -> str:
        """获取存储引擎版本"""
        return "1.0.0"
    
    def is_available(self) -> bool:
        """检查存储引擎是否可用"""
        try:
            self.client.ping()
            return True
        except redis.RedisError:
            return False
    
    def connect(self) -> bool:
        """连接到存储引擎"""
        try:
            self.client.ping()
            return True
        except redis.RedisError as e:
            logging.error(f"Redis连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开与存储引擎的连接"""
        try:
            self.client.close()
            return True
        except redis.RedisError as e:
            logging.error(f"Redis断开连接失败: {e}")
            return False

    def store_conversation(self, user_id: str, user_query: str, bot_response: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """存储单轮对话"""
        try:
            # 检查连接是否可用，如果不可用则尝试重新连接
            if not self.is_available():
                logging.info("Redis连接不可用，尝试重新连接...")
                if not self.connect():
                    logging.error("Redis重新连接失败")
                    return False
            
            key = f"conversation:{user_id}"
            conversation = {
                "query": user_query,
                "response": bot_response,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # 存储对话并限制长度
            self.client.lpush(key, json.dumps(conversation))
            self.client.ltrim(key, 0, self.max_history_rounds * 2 - 1)  # 每轮包含query和response
            # 设置过期时间
            self.client.expire(key, self.default_ttl)
            return True
        except Exception as e:
            logging.error(f"存储对话失败: {e}")
            return False

    def store_coreference(self, user_id: str, pronoun: str, referent_type: str, referent_target: str, referent_value: Any) -> bool:
        """存储指代关系
        
        Args:
            user_id: 用户ID
            pronoun: 代词（如"它"、"这个"）
            referent_type: 指代对象类型（如"entity"）
            referent_target: 指代对象目标（如"stock_code"）
            referent_value: 指代对象值（如"600519.SH"）
            
        Returns:
            bool: 存储结果
        """
        try:
            # 检查连接是否可用，如果不可用则尝试重新连接
            if not self.is_available():
                logging.info("Redis连接不可用，尝试重新连接...")
                if not self.connect():
                    logging.error("Redis重新连接失败")
                    return False
            
            # 存储指代关系的键
            coref_key = f"session:{user_id}:coreferences"
            
            # 不需要在这里更新会话基础信息，会话状态会通过update_session_state方法统一管理
            
            # 存储指代关系
            coreference = {
                "pronoun": pronoun,
                "type": referent_type,
                "target": referent_target,
                "value": referent_value,
                "timestamp": datetime.now().isoformat()
            }
            
            # 将指代关系JSON序列化后添加到集合中
            self.client.sadd(coref_key, json.dumps(coreference))
            
            # 设置过期时间
            self.client.expire(coref_key, self.default_ttl)
            
            return True
        except Exception as e:
            logging.error(f"存储指代关系失败: {e}")
            return False

    def get_coreferences(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的指代关系列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 指代关系列表
        """
        try:
            # 检查连接是否可用，如果不可用则尝试重新连接
            if not self.is_available():
                logging.info("Redis连接不可用，尝试重新连接...")
                if not self.connect():
                    logging.error("Redis重新连接失败")
                    return []
            
            coref_key = f"session:{user_id}:coreferences"
            coreferences = self.client.smembers(coref_key)
            
            # 如果找到指代关系，延长过期时间
            if coreferences:
                self.client.expire(coref_key, self.default_ttl)
                self.client.expire(f"session:{user_id}", self.default_ttl)
            
            return [json.loads(item) for item in coreferences]
        except Exception as e:
            logging.error(f"获取指代关系失败: {e}")
            return []

    def clear_coreferences(self, user_id: str) -> bool:
        """清除用户的指代关系
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 清除结果
        """
        try:
            # 检查连接是否可用，如果不可用则尝试重新连接
            if not self.is_available():
                logging.info("Redis连接不可用，尝试重新连接...")
                if not self.connect():
                    logging.error("Redis重新连接失败")
                    return False
            
            coref_key = f"session:{user_id}:coreferences"
            self.client.delete(coref_key)
            return True
        except Exception as e:
            logging.error(f"清除指代关系失败: {e}")
            return False

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取历史对话记录"""
        try:
            # 检查连接是否可用，如果不可用则尝试重新连接
            if not self.is_available():
                logging.info("Redis连接不可用，尝试重新连接...")
                if not self.connect():
                    logging.error("Redis重新连接失败")
                    return []
            
            key = f"conversation:{user_id}"
            history = self.client.lrange(key, 0, limit - 1)
            if history:
                # 延长会话过期时间（滑动过期）
                self.client.expire(key, self.default_ttl)
                logging.info(f"从Redis获取到历史对话: {history}")
            return [json.loads(item) for item in history[::-1]]  # 正序返回
        except Exception as e:
            logging.error(f"获取对话历史失败: {e}")
            return []

    def update_session_state(self, user_id: str, session_state: Dict[str, Any]) -> bool:
        """更新会话状态"""
        try:
            key = f"session:{user_id}"
            session_state['last_active_time'] = datetime.now().isoformat()
            # 使用setex设置值并同时设置过期时间
            self.client.setex(key, self.default_ttl, json.dumps(session_state))
            return True
        except Exception as e:
            logging.error(f"更新会话状态失败: {e}")
            return False

    def get_session_state(self, user_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        try:
            key = f"session:{user_id}"
            state = self.client.get(key)
            if state:
                # 延长会话过期时间（滑动过期）
                self.client.expire(key, self.default_ttl)
                return json.loads(state)
            # 返回默认会话状态
            return {
                'user_id': user_id,
                'current_stock': {},
                'history': [],
                'pending_entities': {},
                'last_active_time': datetime.now().isoformat(),
                'preferences': {}
            }
        except Exception as e:
            logging.error(f"获取会话状态失败: {e}")
            return {
                'user_id': user_id,
                'current_stock': {},
                'history': [],
                'pending_entities': {},
                'last_active_time': datetime.now().isoformat(),
                'preferences': {}
            }

    def clear_conversation(self, user_id: str) -> bool:
        """清除用户对话历史"""
        try:
            key = f"conversation:{user_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logging.error(f"清除对话历史失败: {e}")
            return False

    def set_pending_entities(self, user_id: str, entities: Dict[str, Any]) -> bool:
        """设置待处理实体"""
        try:
            key = f"pending_entities:{user_id}"
            # 使用setex设置值并同时设置过期时间
            self.client.setex(key, self.default_ttl, json.dumps(entities))
            return True
        except Exception as e:
            logging.error(f"设置待处理实体失败: {e}")
            return False

    def get_pending_entities(self, user_id: str) -> Dict[str, Any]:
        """获取待处理实体"""
        try:
            key = f"pending_entities:{user_id}"
            entities = self.client.get(key)
            if entities:
                # 延长会话过期时间（滑动过期）
                self.client.expire(key, self.default_ttl)
                return json.loads(entities)
            return {}
        except Exception as e:
            logging.error(f"获取待处理实体失败: {e}")
            return {}

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """更新用户偏好"""
        try:
            key = f"preferences:{user_id}"
            current_prefs = self.get_user_preferences(user_id)
            current_prefs.update(preferences)
            # 使用setex设置值并同时设置过期时间
            self.client.setex(key, self.default_ttl, json.dumps(current_prefs))
            return True
        except Exception as e:
            logging.error(f"更新用户偏好失败: {e}")
            return False

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
        try:
            key = f"preferences:{user_id}"
            prefs = self.client.get(key)
            if prefs:
                # 延长会话过期时间（滑动过期）
                self.client.expire(key, self.default_ttl)
                return json.loads(prefs)
            return {}
        except Exception as e:
            logging.error(f"获取用户偏好失败: {e}")
            return {}

    def set_expire(self, user_id: str, expire_seconds: int) -> bool:
        """设置会话过期时间"""
        try:
            keys = [
                f"conversation:{user_id}",
                f"session:{user_id}",
                f"pending_entities:{user_id}",
                f"preferences:{user_id}"
            ]
            for key in keys:
                if self.client.exists(key):
                    self.client.expire(key, expire_seconds)
            return True
        except Exception as e:
            logging.error(f"设置会话过期时间失败: {e}")
            return False

    def get_active_users(self, pattern: str = "*", limit: int = 100) -> List[str]:
        """获取活跃用户列表"""
        try:
            keys = self.client.keys(f"conversation:{pattern}")
            users = []
            for key in keys[:limit]:
                user_id = key.replace("conversation:", "")
                users.append(user_id)
            return users
        except Exception as e:
            logging.error(f"获取活跃用户列表失败: {e}")
            return []
    
    def extend_session_timeout(self, user_id: str, timeout_seconds: int = None) -> bool:
        """延长会话过期时间"""
        try:
            expire_time = timeout_seconds or self.default_ttl
            keys = [
                f"conversation:{user_id}",
                f"session:{user_id}",
                f"pending_entities:{user_id}",
                f"preferences:{user_id}"
            ]
            for key in keys:
                if self.client.exists(key):
                    self.client.expire(key, expire_time)
            return True
        except Exception as e:
            logging.error(f"延长会话过期时间失败: {e}")
            return False


def build_context_prompt(user_id: str, session_manager: RedisSessionManager, current_query: str) -> str:
    """构建包含历史上下文的提示词"""
    history = session_manager.get_conversation_history(user_id)

    context = "以下是历史对话记录：\n"
    for i, turn in enumerate(history):
        context += f"用户[{i + 1}]: {turn['query']}\n"
        context += f"助手[{i + 1}]: {turn['response']}\n"

    context += f"\n当前用户提问: {current_query}\n请基于历史对话和当前问题，给出连贯且准确的回答。"
    return context