import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.tool_integration import FinancialDataAPI

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试ETF查询功能
def test_etf_query():
    logger.info("测试ETF查询功能")
    
    # 创建API实例
    api = FinancialDataAPI()
    
    # 测试黄金ETF基金 (159937)
    logger.info("\n=== 测试黄金ETF基金 (159937) ===")
    try:
        etf_price = api.get_stock_price("159937")
        logger.info(f"ETF价格数据: {etf_price}")
        
        # 检查返回结果
        if etf_price and 'price' in etf_price:
            logger.info("✓ 成功获取ETF价格数据")
        else:
            logger.error("✗ 获取ETF价格数据失败")
    except Exception as e:
        logger.error(f"获取ETF价格数据出错: {e}")
    
    # 测试ETF历史数据
    logger.info("\n=== 测试ETF历史数据查询 ===")
    try:
        import datetime
        
        # 直接测试AkShare的fund_etf_hist_em函数
        import akshare as ak
        logger.info("直接测试AkShare获取ETF历史数据...")
        ak_data = ak.fund_etf_hist_em(
            symbol="159937",
            start_date="20240101",
            end_date="20240331"
        )
        logger.info(f"AkShare直接调用结果形状: {ak_data.shape}")
        logger.info(f"AkShare直接调用结果前5行: {ak_data.head()}")
        
        # 调用API的历史数据方法
        etf_historical = api.get_historical_data(
            "159937", 
            start_date=datetime.datetime(2024, 1, 1),
            end_date=datetime.datetime(2024, 3, 31),
            interval="1d"
        )
        logger.info(f"ETF历史数据: {etf_historical}")
        
        if etf_historical and 'data' in etf_historical and etf_historical['data']:
            logger.info(f"✓ 成功获取ETF历史数据，共 {len(etf_historical['data'])} 条记录")
            logger.info(f"第一条记录: {etf_historical['data'][0]}")
        else:
            logger.error("✗ 获取ETF历史数据失败")
    except Exception as e:
        logger.error(f"获取ETF历史数据出错: {e}")
        import traceback
        traceback.print_exc()

# 测试通过名称查询ETF
def test_etf_query_by_name():
    logger.info("\n=== 测试通过名称查询ETF ===")
    
    # 首先需要确保ETF名称已经在股票映射中
    from core.langchain_tools import STOCK_NAME_TO_CODE
    
    logger.info("检查股票映射中是否包含ETF名称")
    logger.info(f"股票映射中包含 {len(STOCK_NAME_TO_CODE)} 个条目")
    
    # 查看是否有ETF相关的条目
    etf_entries = {k: v for k, v in STOCK_NAME_TO_CODE.items() if 'ETF' in k or 'etf' in k}
    if etf_entries:
        logger.info(f"找到 {len(etf_entries)} 个ETF相关条目: {etf_entries}")
    else:
        logger.info("没有找到ETF相关条目")
        logger.info("需要手动添加ETF名称到股票映射中")

if __name__ == "__main__":
    logger.info("开始测试ETF查询功能")
    test_etf_query()
    test_etf_query_by_name()
    logger.info("ETF查询功能测试完成")