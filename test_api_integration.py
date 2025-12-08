# API集成测试脚本
import yaml
import logging
from core.tool_integration import FinancialDataAPI

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_api_keys():
    """加载API密钥配置"""
    try:
        with open('config/api_keys.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载API配置失败: {e}")
        return None

def test_stock_api():
    """测试股票API"""
    logger.info("\n=== 测试股票API ===")
    api_keys = load_api_keys()
    if not api_keys:
        return False
        
    financial_api = FinancialDataAPI(api_keys)
    
    # 测试苹果股票价格
    logger.info("测试获取苹果股票价格...")
    stock_data = financial_api.get_stock_price("AAPL")
    if stock_data:
        logger.info(f"获取成功: {stock_data}")
    else:
        logger.error("获取失败")
        return False
        
    # 测试股票日内数据
    logger.info("测试获取苹果股票日内数据...")
    intraday_data = financial_api.get_stock_intraday("AAPL")
    if intraday_data:
        logger.info(f"获取成功: 数据点数量 - {len(intraday_data.get('Time Series (5min)', {}))}")
    else:
        logger.error("获取失败")
        return False
    
    return True

def test_market_api():
    """测试市场指数API"""
    logger.info("\n=== 测试市场指数API ===")
    api_keys = load_api_keys()
    if not api_keys:
        return False
        
    financial_api = FinancialDataAPI(api_keys)
    
    # 测试道琼斯指数
    logger.info("测试获取道琼斯指数...")
    index_data = financial_api.get_market_index("DJI")
    if index_data:
        logger.info(f"获取成功: {index_data}")
    else:
        logger.error("获取失败")
        return False
        
    # 测试标普500指数
    logger.info("测试获取标普500指数...")
    index_data = financial_api.get_market_index("SPX")
    if index_data:
        logger.info(f"获取成功: {index_data}")
    else:
        logger.error("获取失败")
        return False
    
    return True

def test_news_api():
    """测试新闻API"""
    logger.info("\n=== 测试新闻API ===")
    api_keys = load_api_keys()
    if not api_keys:
        return False
        
    financial_api = FinancialDataAPI(api_keys)
    
    # 测试获取财经新闻
    logger.info("测试获取财经新闻...")
    news_data = financial_api.get_financial_news("股票", limit=3)
    if news_data:
        articles = news_data.get('articles', [])
        logger.info(f"获取成功: {len(articles)}条新闻")
        for i, article in enumerate(articles[:3]):
            logger.info(f"[{i+1}] {article.get('title')}")
    else:
        logger.error("获取失败")
        return False
    
    return True

def main():
    """主测试函数"""
    logger.info("开始API集成测试...")
    
    # 运行所有测试
    results = {
        "stock_api": test_stock_api(),
        "market_api": test_market_api(),
        "news_api": test_news_api()
    }
    
    # 打印测试结果
    logger.info("\n=== 测试结果汇总 ===")
    for test_name, result in results.items():
        status = "✅ 成功" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    # 检查是否所有测试都通过
    if all(results.values()):
        logger.info("\n🎉 所有API测试都通过了！")
        return 0
    else:
        logger.error("\n❌ 部分API测试失败！")
        return 1

if __name__ == "__main__":
    exit(main())