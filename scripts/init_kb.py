# 知识库初始化脚本
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_base import FinancialKnowledgeBase
from utils.logging import default_logger
from utils.config_loader import default_config_loader


def init_knowledge_base():
    """初始化知识库（创建表和集合）"""
    try:
        default_logger.info("开始初始化知识库...")
        
        # 加载数据库配置
        db_config = default_config_loader.load_config("database.yaml")
        mysql_config = default_config_loader.get("database.yaml", "mysql", {})
        
        # 初始化知识库（会自动创建表和集合）
        kb = FinancialKnowledgeBase(
            mysql_host=mysql_config.get("host", "localhost"),
            mysql_user=mysql_config.get("user", "root"),
            mysql_password=mysql_config.get("password", "lincy123"),
            mysql_db=mysql_config.get("database", "financial_rag"),
            milvus_host=db_config.get("milvus", {}).get("host", "localhost"),
            milvus_port=db_config.get("milvus", {}).get("port", 19530)
        )
        
        default_logger.info("知识库初始化完成！")
        default_logger.info("- MySQL表已创建")
        default_logger.info("- Milvus集合已创建")
        
        kb.close_connections()
        
    except Exception as e:
        default_logger.error(f"知识库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_knowledge_base()