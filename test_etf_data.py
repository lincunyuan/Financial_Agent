import akshare as ak
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试获取ETF列表
def test_etf_list():
    logger.info("测试获取ETF列表")
    try:
        # 尝试获取ETF列表
        etf_list = ak.fund_etf_spot_em()
        logger.info(f"成功获取 {len(etf_list)} 只ETF列表")
        logger.info(f"ETF列表前10行:")
        logger.info(etf_list.head(10))
        logger.info(f"ETF列表列名: {etf_list.columns.tolist()}")
        return etf_list
    except Exception as e:
        logger.error(f"获取ETF列表失败: {e}")
        return None

# 测试获取特定ETF数据
def test_etf_data(etf_code):
    logger.info(f"测试获取ETF {etf_code} 的数据")
    try:
        # 尝试获取ETF实时数据
        etf_data = ak.fund_etf_spot_em()
        target_etf = etf_data[etf_data['代码'] == etf_code]
        if not target_etf.empty:
            logger.info(f"成功获取ETF {etf_code} 的实时数据:")
            logger.info(target_etf.iloc[0].to_dict())
            return target_etf.iloc[0].to_dict()
        else:
            logger.warning(f"未找到ETF {etf_code}")
            return None
    except Exception as e:
        logger.error(f"获取ETF数据失败: {e}")
        return None

# 测试获取ETF历史数据
def test_etf_historical_data(etf_code, start_date="20240101", end_date="20240630"):
    logger.info(f"测试获取ETF {etf_code} 的历史数据")
    try:
        # 尝试获取ETF历史数据
        etf_historical = ak.fund_etf_hist_em(symbol=etf_code, start_date=start_date, end_date=end_date)
        logger.info(f"成功获取 {len(etf_historical)} 条ETF历史数据")
        logger.info(f"ETF历史数据前5行:")
        logger.info(etf_historical.head())
        logger.info(f"ETF历史数据列名: {etf_historical.columns.tolist()}")
        return etf_historical
    except Exception as e:
        logger.error(f"获取ETF历史数据失败: {e}")
        return None

# 测试特定ETF：黄金ETF(159937)
def test_gold_etf():
    logger.info("\n=== 测试黄金ETF(159937) ===")
    etf_code = "159937"
    
    # 测试实时数据
    realtime_data = test_etf_data(etf_code)
    
    # 测试历史数据
    historical_data = test_etf_historical_data(etf_code)
    
    return realtime_data, historical_data

if __name__ == "__main__":
    logger.info("开始测试ETF数据获取功能")
    
    # 测试获取ETF列表
    etf_list = test_etf_list()
    
    # 测试特定ETF
    realtime_data, historical_data = test_gold_etf()
    
    logger.info("ETF数据测试完成")