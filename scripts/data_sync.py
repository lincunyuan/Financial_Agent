# 财经数据同步脚本
import sys
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.knowledge_base import FinancialKnowledgeBase
from utils.logging import default_logger
from utils.config_loader import default_config_loader


def sync_financial_news(urls: List[str]):
    """
    同步财经新闻到知识库
    
    Args:
        urls: 新闻URL列表
    """
    try:
        default_logger.info(f"开始同步 {len(urls)} 条财经新闻...")
        
        # 加载数据库配置
        db_config = default_config_loader.load_config("database.yaml")
        mysql_config = default_config_loader.get("database.yaml", "mysql", {})
        
        # 初始化知识库
        kb = FinancialKnowledgeBase(
            mysql_host=mysql_config.get("host", "localhost"),
            mysql_user=mysql_config.get("user", "root"),
            mysql_password=mysql_config.get("password", ""),
            mysql_db=mysql_config.get("database", "financial_rag"),
            milvus_host=db_config.get("milvus", {}).get("host", "localhost"),
            milvus_port=db_config.get("milvus", {}).get("port", 19530)
        )
        
        # 同步每条新闻
        success_count = 0
        for i, url in enumerate(urls, 1):
            try:
                default_logger.info(f"[{i}/{len(urls)}] 处理: {url}")
                
                # 爬取新闻内容
                document = kb.crawl_financial_news(url)
                
                # 添加到知识库
                kb.add_document_to_kb(document)
                
                success_count += 1
                default_logger.info(f"✓ 成功添加: {document['title']}")
                
            except Exception as e:
                default_logger.error(f"✗ 处理失败 {url}: {e}")
                continue
        
        default_logger.info(f"\n同步完成！成功: {success_count}/{len(urls)}")
        
        kb.close_connections()
        
    except Exception as e:
        default_logger.error(f"数据同步失败: {e}")
        sys.exit(1)


def sync_from_file(url_file: str):
    """
    从文件读取URL列表并同步
    
    Args:
        url_file: 包含URL的文件路径（每行一个URL）
    """
    urls = []
    try:
        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        if not urls:
            default_logger.warning("文件中没有找到有效的URL")
            return
        
        sync_financial_news(urls)
        
    except FileNotFoundError:
        default_logger.error(f"文件不存在: {url_file}")
        sys.exit(1)
    except Exception as e:
        default_logger.error(f"读取文件失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="同步财经新闻到知识库")
    parser.add_argument("--urls", nargs="+", help="新闻URL列表")
    parser.add_argument("--file", type=str, help="包含URL的文件路径（每行一个URL）")
    
    args = parser.parse_args()
    
    if args.file:
        sync_from_file(args.file)
    elif args.urls:
        sync_financial_news(args.urls)
    else:
        parser.print_help()
        sys.exit(1)