# Redis会话管理（对话存储与上下文构建）
import redis
import json
from datetime import datetime
from typing import Dict, List, Optional
from utils.config_loader import default_config_loader


class RedisSessionManager:
    def __init__(self, host: str = None, port: int = None, db: int = None, password: str = None):
        """初始化Redis连接"""
        # 从配置文件加载默认配置
        redis_config = default_config_loader.get("database.yaml", "redis", {})
        
        # 使用传入参数或配置文件中的值
        self.host = host or redis_config.get("host", "localhost")
        self.port = port or redis_config.get("port", 6379)
        self.db = db or redis_config.get("db", 0)
        self.password = password or redis_config.get("password")
        
        # 建立Redis连接
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_connect_timeout=5,
            decode_responses=True
        )
        self.max_history_rounds = 5  # 保留最近5轮对话

    def store_conversation(self, user_id: str, user_query: str, bot_response: str) -> None:
        """存储单轮对话"""
        key = f"conversation:{user_id}"
        conversation = {
            "query": user_query,
            "response": bot_response,
            "timestamp": datetime.now().isoformat()
        }

        # 存储对话并限制长度
        self.client.lpush(key, json.dumps(conversation))
        self.client.ltrim(key, 0, self.max_history_rounds * 2 - 1)  # 每轮包含query和response

    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """获取历史对话记录"""
        key = f"conversation:{user_id}"
        history = self.client.lrange(key, 0, -1)
        return [json.loads(item) for item in history[::-1]]  # 正序返回

    def clear_conversation(self, user_id: str) -> None:
        """清除用户对话历史"""
        key = f"conversation:{user_id}"
        self.client.delete(key)


def build_context_prompt(user_id: str, session_manager: RedisSessionManager, current_query: str) -> str:
    """构建包含历史上下文的提示词"""
    history = session_manager.get_conversation_history(user_id)

    context = "以下是历史对话记录：\n"
    for i, turn in enumerate(history):
        context += f"用户[{i + 1}]: {turn['query']}\n"
        context += f"助手[{i + 1}]: {turn['response']}\n"

    context += f"\n当前用户提问: {current_query}\n请基于历史对话和当前问题，给出连贯且准确的回答。"
    return context