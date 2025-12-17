# LangChain工具封装 - 将现有API转换为LangChain Tool
from langchain.tools import tool, BaseTool
from typing import Dict, Optional, List, Any
from datetime import datetime
from core.tool_integration import FinancialDataAPI
from core.chart_generator import ChartGenerator  # 添加ChartGenerator的导入
from utils.config_loader import default_config_loader
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 初始化配置和数据API
config_loader = default_config_loader
api_keys = config_loader.load_config("api_keys.yaml")
financial_api = FinancialDataAPI(api_keys)

import os
import pandas as pd

# 加载股票名称到代码的映射
STOCK_NAME_TO_CODE = {}

def load_stock_mapping():
    """
    从CSV文件加载股票名称到代码的映射
    """
    global STOCK_NAME_TO_CODE
    
    try:
        # 构建CSV文件路径
        csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "stock_mapping.csv")
        
        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            logger.warning(f"股票映射CSV文件不存在: {csv_file_path}")
            # 如果文件不存在，使用默认映射
            STOCK_NAME_TO_CODE = {
                "贵州茅台": "600519.SS",
                "宁德时代": "300750.SZ",
                "招商银行": "600036.SS",
                "比亚迪": "002594.SZ",
                "平安银行": "000001.SZ",
                "兴业银行": "601166.SS",
                "中国平安": "601318.SS",
                "工商银行": "601398.SS",
                "建设银行": "601939.SS",
                "中国石油": "601857.SS",
                "上海电力": "600021.SS",
                "神州信息": "000555.SZ",
                "阿里巴巴": "BABA.US",
                "腾讯控股": "00700.HK",
                "百度": "BIDU.US",
                "京东": "JD.US",
                "美团": "03690.HK",
                "拼多多": "PDD.US",
                "小米集团": "01810.HK",
                "网易": "NTES.US",
                "新浪": "SINA.US",
                "搜狐": "SOHU.US"
            }
            return
        
        # 从CSV文件加载股票映射
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
        
        # 修复股票代码格式并构建映射
        stock_mapping = {}
        for _, row in df.iterrows():
            if len(row) >= 2:
                stock_name = row['股票名称'].strip()
                stock_code = row['股票代码'].strip()
                
                # 修复股票代码格式 - 去除可能的sh/sz前缀
                if stock_code.startswith(('sh', 'sz')):
                    stock_code = stock_code[2:]
                
                # 确保股票代码格式正确
                if not stock_code.endswith(('.SS', '.SZ', '.HK', '.US')):
                    # 根据A股代码规则添加交易所后缀
                    if stock_code.startswith(('0', '3')):
                        stock_code += '.SZ'
                    elif stock_code.startswith('6'):
                        stock_code += '.SS'
                
                stock_mapping[stock_name] = stock_code
        
        STOCK_NAME_TO_CODE = stock_mapping
        logger.info(f"成功从CSV文件加载了 {len(STOCK_NAME_TO_CODE)} 条股票映射记录")
        
    except Exception as e:
        logger.error(f"加载股票映射失败: {e}")
        # 如果加载失败，使用默认映射
        STOCK_NAME_TO_CODE = {
            "贵州茅台": "600519.SS",
            "宁德时代": "300750.SZ",
            "招商银行": "600036.SS",
            "比亚迪": "002594.SZ",
            "平安银行": "000001.SZ",
            "兴业银行": "601166.SS",
            "中国平安": "601318.SS",
            "工商银行": "601398.SS",
            "建设银行": "601939.SS",
            "中国石油": "601857.SS",
            "上海电力": "600021.SS",
            "神州信息": "000555.SZ",
            "阿里巴巴": "BABA.US",
            "腾讯控股": "00700.HK",
            "百度": "BIDU.US",
            "京东": "JD.US",
            "美团": "03690.HK",
            "拼多多": "PDD.US",
            "小米集团": "01810.HK",
            "网易": "NTES.US",
            "新浪": "SINA.US",
            "搜狐": "SOHU.US"
        }

# 在模块加载时自动加载股票映射
load_stock_mapping()

# 指数名称到代码的映射
INDEX_NAME_TO_CODE = {
    "上证指数": "000001",
    "深证成指": "399001",
    "创业板指": "399006",
    "沪深300": "000300",
    "上证50": "000016"
}

@tool(return_direct=False)
def get_stock_price(stock_name_or_code: str, time: Optional[str] = None) -> Dict[str, Any]:
    """获取股票实时/历史价格数据
    
    Args:
        stock_name_or_code: 股票名称或代码（如："贵州茅台"或"600519.SS"或"600519"）
        time: 时间（可选，格式：YYYY-MM-DD）
        
    Returns:
        Dict: 包含股票价格、涨跌幅等信息的字典
    """
    try:
        # 处理股票名称到代码的映射
        if stock_name_or_code in STOCK_NAME_TO_CODE:
            stock_code = STOCK_NAME_TO_CODE[stock_name_or_code]
        elif len(stock_name_or_code) == 6 and stock_name_or_code.isdigit():
            # 处理6位数字代码 - 支持所有沪深A股股票
            # 000、002、300开头的股票属于深交所(.SZ)
            # 600、601、603、605开头的股票属于上交所(.SS)
            if stock_name_or_code.startswith(('000', '002', '300')):
                stock_code = f"{stock_name_or_code}.SZ"
            else:
                stock_code = f"{stock_name_or_code}.SS"
        elif stock_name_or_code.endswith(('.SS', '.SZ')):
            # 已经包含交易所后缀的完整代码
            stock_code = stock_name_or_code
        else:
            stock_code = stock_name_or_code
        
        # 转换时间参数
        time_obj = datetime.strptime(time, "%Y-%m-%d") if time else None
        
        # 调用API
        result = financial_api.get_stock_price(stock_code, time_obj)
        
        # 添加上下文信息
        result["tool_used"] = "get_stock_price"
        result["input_query"] = stock_name_or_code
        
        return result
        
    except Exception as e:
        logger.error(f"调用股票价格工具失败: {e}")
        return {
            "error": str(e),
            "tool_used": "get_stock_price",
            "input_query": stock_name_or_code
        }

@tool(return_direct=False)
def get_market_index(index_name: str, time: Optional[str] = None) -> Dict[str, Any]:
    """获取市场指数数据
    
    Args:
        index_name: 指数名称（如："上证指数"、"深证成指"）
        time: 时间（可选，格式：YYYY-MM-DD）
        
    Returns:
        Dict: 包含指数价格、涨跌幅等信息的字典
    """
    try:
        # 转换时间参数
        time_obj = datetime.strptime(time, "%Y-%m-%d") if time else None
        
        # 调用API
        result = financial_api.get_market_index(index_name, time_obj)
        
        # 添加上下文信息
        result["tool_used"] = "get_market_index"
        result["input_query"] = index_name
        
        return result
        
    except Exception as e:
        logger.error(f"调用市场指数工具失败: {e}")
        return {
            "error": str(e),
            "tool_used": "get_market_index",
            "input_query": index_name
        }

@tool(return_direct=False)
def get_financial_news(category: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """获取财经新闻
    
    Args:
        category: 新闻类别（可选，如："宏观经济"、"股市"、"债市"）
        limit: 返回新闻数量（默认10条）
        
    Returns:
        Dict: 包含新闻列表的字典
    """
    try:
        # 调用API
        result = financial_api.get_financial_news(category, limit)
        
        # 添加上下文信息
        result["tool_used"] = "get_financial_news"
        result["input_query"] = category if category else "全部"
        
        return result
        
    except Exception as e:
        logger.error(f"调用财经新闻工具失败: {e}")
        return {
            "error": str(e),
            "tool_used": "get_financial_news",
            "input_query": category
        }

@tool(return_direct=False)
def get_economic_data(indicator: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """获取经济数据
    
    Args:
        indicator: 经济指标（如："GDP"、"CPI"、"PPI"）
        start_date: 开始日期（格式：YYYY-MM-DD）
        end_date: 结束日期（格式：YYYY-MM-DD）
        
    Returns:
        Dict: 包含经济数据的字典
    """
    try:
        # 转换日期参数
        start_obj = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # 调用API
        result = financial_api.get_economic_data(indicator, start_obj, end_obj)
        
        # 添加上下文信息
        result["tool_used"] = "get_economic_data"
        result["input_query"] = indicator
        
        return result
        
    except Exception as e:
        logger.error(f"调用经济数据工具失败: {e}")
        return {
            "error": str(e),
            "tool_used": "get_economic_data",
            "input_query": indicator
        }

@tool(return_direct=False)
def get_stock_historical_data(stock_name_or_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None, interval: str = "1d") -> Dict[str, Any]:
    """获取股票历史K线数据
    
    Args:
        stock_name_or_code: 股票名称或代码（如："贵州茅台"或"600519.SS"或"600519"）
        start_date: 开始日期（可选，格式：YYYY-MM-DD）
        end_date: 结束日期（可选，格式：YYYY-MM-DD）
        interval: 时间间隔（可选，如："1d"、"1w"、"1mo"）
        
    Returns:
        Dict: 包含股票历史K线数据的字典
    """
    try:
        # 清理输入：去除空格和特殊字符
        clean_input = stock_name_or_code.strip().replace(' ', '')
        
        # 处理股票名称到代码的映射
        if clean_input in STOCK_NAME_TO_CODE:
            stock_code = STOCK_NAME_TO_CODE[clean_input]
        elif len(clean_input) == 6 and clean_input.isdigit():
            # 处理6位数字代码 - 支持所有沪深A股股票
            # 000、002、300开头的股票属于深交所(.SZ)
            # 600、601、603、605开头的股票属于上交所(.SS)
            if clean_input.startswith(('000', '002', '300')):
                stock_code = f"{clean_input}.SZ"
            else:
                stock_code = f"{clean_input}.SS"
        elif clean_input.endswith(('.SS', '.SZ')):
            # 已经包含交易所后缀的完整代码
            stock_code = clean_input
        # 处理带sh/sz前缀的代码
        elif clean_input.startswith('sh'):
            stock_code = clean_input[2:] + '.SS'
        elif clean_input.startswith('sz'):
            stock_code = clean_input[2:] + '.SZ'
        else:
            stock_code = clean_input
        
        # 转换日期参数
        if not start_date:
            # 默认开始日期改为2000-01-01，确保显示完整历史数据
            start_date = "2000-01-01"
        
        if not end_date:
            # 默认结束日期为当前日期
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        start_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_obj = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 调用API
        result = financial_api.get_historical_data(stock_code, start_obj, end_obj, interval)
        
        # 添加上下文信息
        result["tool_used"] = "get_stock_historical_data"
        result["input_query"] = stock_name_or_code
        
        return result
        
    except Exception as e:
        logger.error(f"调用股票历史数据工具失败: {e}")
        return {
            "error": str(e),
            "tool_used": "get_stock_historical_data",
            "input_query": stock_name_or_code
        }

@tool(return_direct=False)
def generate_stock_charts(stock_name_or_code: str, chart_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """生成股票图表（K线图、折线图、成交量图）
    
    Args:
        stock_name_or_code: 股票名称或代码（如："贵州茅台"或"600519.SS"或"600519"）
        chart_types: 要生成的图表类型列表，可选值：["k_line", "line", "volume"]，默认生成所有图表
        
    Returns:
        Dict: 包含生成的图表路径信息的字典
    """
    try:
        # 处理股票名称到代码的映射
        if stock_name_or_code in STOCK_NAME_TO_CODE:
            stock_code = STOCK_NAME_TO_CODE[stock_name_or_code]
        elif len(stock_name_or_code) == 6 and stock_name_or_code.isdigit():
            # 处理6位数字代码 - 支持所有沪深A股股票
            # 000、002、300开头的股票属于深交所(.SZ)
            # 600、601、603、605开头的股票属于上交所(.SS)
            if stock_name_or_code.startswith(('000', '002', '300')):
                stock_code = f"{stock_name_or_code}.SZ"
            else:
                stock_code = f"{stock_name_or_code}.SS"
        elif stock_name_or_code.endswith(('.SS', '.SZ')):
            # 已经包含交易所后缀的完整代码
            stock_code = stock_name_or_code
        else:
            stock_code = stock_name_or_code
        
        logger.info(f"生成股票图表: {stock_code}, 类型: {chart_types}")
        
        # 获取历史数据
        historical_data = financial_api.get_historical_data(stock_code)
        if not historical_data:
            return {"error": "无法获取历史数据", "tool_used": "generate_stock_charts"}
        
        # 转换数据格式：英文键名转为中文列名，以便ChartGenerator使用
        import pandas as pd
        df = pd.DataFrame(historical_data)
        
        # 处理不同数量的列（兼容可能的字段变化）
        try:
            if len(df.columns) == 10:
                df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '涨跌幅', '股票代码', 'symbol']
            elif len(df.columns) == 9:
                df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '涨跌幅', '股票代码']
            else:
                logger.error(f"未知的数据列数: {len(df.columns)}")
                return {"error": "数据格式错误"}
                
            # 如果有symbol列，可以保留也可以删除，这里选择保留
            # 但确保数据包含ChartGenerator所需的所有必要列
            required_columns = ['日期', '开盘', '最高', '最低', '收盘', '成交量', '成交额', '涨跌幅']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"缺少必要的列: {[col for col in required_columns if col not in df.columns]}")
                return {"error": "数据格式不完整"}
        except Exception as e:
            logger.error(f"转换数据格式时出错: {e}")
            return {"error": "数据处理失败"}
        
        # 创建图表生成器
        chart_generator = ChartGenerator()
        
        # 如果没有指定图表类型，生成所有图表
        if not chart_types:
            chart_types = ["k_line", "line", "volume"]
        
        # 生成并保存图表
        saved_charts = {}
        
        # 生成K线图
        if "k_line" in chart_types:
            k_line_fig = chart_generator.generate_k_line_chart(stock_code, df)
            if k_line_fig:
                saved_charts["k_line"] = chart_generator.save_chart(k_line_fig, f"{stock_code}_kline", "html")
        
        # 生成收盘价折线图
        if "line" in chart_types:
            line_fig = chart_generator.generate_line_chart(stock_code, df)
            if line_fig:
                saved_charts["line"] = chart_generator.save_chart(line_fig, f"{stock_code}_line", "html")
        
        # 生成成交量图
        if "volume" in chart_types:
            volume_fig = chart_generator.generate_volume_chart(stock_code, df)
            if volume_fig:
                saved_charts["volume"] = chart_generator.save_chart(volume_fig, f"{stock_code}_volume", "html")
        
        if not saved_charts:
            return {"error": "无法生成图表", "tool_used": "generate_stock_charts"}
        
        return {
            "symbol": stock_code,
            "charts": saved_charts,
            "message": f"成功生成{stock_code}的图表",
            "tool_used": "generate_stock_charts"
        }
        
    except Exception as e:
        logger.error(f"生成股票图表失败: {e}")
        return {
            "error": str(e),
            "tool_used": "generate_stock_charts",
            "input_query": stock_name_or_code
        }

# 获取所有LangChain工具
def get_all_langchain_tools() -> List[BaseTool]:
    """获取所有LangChain工具"""
    return [
        get_stock_price,
        get_market_index,
        get_financial_news,
        get_economic_data,
        get_stock_historical_data,
        generate_stock_charts
    ]