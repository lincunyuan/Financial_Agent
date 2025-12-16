# 测试历史数据获取功能
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath('.'))

from core.tool_integration import FinancialDataAPI
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_historical_data():
    """测试历史数据获取功能"""
    logger.info("开始测试历史数据获取功能")
    
    # 创建API实例
    api = FinancialDataAPI()
    
    # 测试1: A股历史数据
    logger.info("\n1. 测试A股历史数据获取")
    try:
        stock_data = api.get_historical_data("600519.SS", interval="1d", start_date="2023-01-01", end_date="2023-01-31")
        if stock_data:
            logger.info(f"成功获取贵州茅台历史数据: {len(stock_data)}条")
            logger.info(f"第一条数据: {stock_data[0]}")
            logger.info(f"最后一条数据: {stock_data[-1]}")
        else:
            logger.error("获取A股历史数据失败")
    except Exception as e:
        logger.error(f"测试A股历史数据失败: {e}", exc_info=True)
    
    # 测试2: ETF历史数据
    logger.info("\n2. 测试ETF历史数据获取")
    try:
        etf_data = api.get_historical_data("510050.SS", interval="1d", start_date="2023-01-01", end_date="2023-01-31")
        if etf_data:
            logger.info(f"成功获取华夏上证50ETF历史数据: {len(etf_data)}条")
            logger.info(f"第一条数据: {etf_data[0]}")
            logger.info(f"最后一条数据: {etf_data[-1]}")
        else:
            logger.error("获取ETF历史数据失败")
    except Exception as e:
        logger.error(f"测试ETF历史数据失败: {e}", exc_info=True)
    
    # 测试3: 港股历史数据
    logger.info("\n3. 测试港股历史数据获取")
    try:
        hk_data = api.get_historical_data("0700.HK", interval="1d", start_date="2023-01-01", end_date="2023-01-31")
        if hk_data:
            logger.info(f"成功获取腾讯控股历史数据: {len(hk_data)}条")
            logger.info(f"第一条数据: {hk_data[0]}")
            logger.info(f"最后一条数据: {hk_data[-1]}")
        else:
            logger.error("获取港股历史数据失败")
    except Exception as e:
        logger.error(f"测试港股历史数据失败: {e}", exc_info=True)
    
    # 测试4: 不同时间周期
    logger.info("\n4. 测试不同时间周期")
    try:
        weekly_data = api.get_historical_data("600519.SS", interval="1w", start_date="2023-01-01", end_date="2023-06-30")
        if weekly_data:
            logger.info(f"成功获取贵州茅台周线数据: {len(weekly_data)}条")
            logger.info(f"第一条周线数据: {weekly_data[0]}")
    except Exception as e:
        logger.error(f"测试周线数据失败: {e}", exc_info=True)
    
    logger.info("\n历史数据获取功能测试完成")


if __name__ == "__main__":
    test_historical_data()