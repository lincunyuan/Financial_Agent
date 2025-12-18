import requests
import datetime
import logging
from typing import Optional, Dict, List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

# 配置日志
logger = logging.getLogger(__name__)

# 新浪财经API基础URL
SINA_API_URL = "https://hq.sinajs.cn/list={}"

# 伪装User-Agent和其他请求头，避免被反爬
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive"
}


def get_stock_realtime_data(symbol: str) -> Optional[Dict]:
    """
    使用新浪财经API获取实时股价数据
    
    Args:
        symbol: 股票代码，格式如"sh600519"（上证）或"sz000001"（深证）
        
    Returns:
        Dict: 包含股票实时数据的字典，失败返回None
    """
    try:
        # 构造请求URL
        url = SINA_API_URL.format(symbol)
        
        # 发送请求
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        
        # 解析返回数据
        # 返回格式：var hq_str_sh600519="贵州茅台,1700.00,1698.00,1705.00,1710.00,1695.00,1699.99,1700.00,100,100000,10000000,...";
        data_str = response.text.split('="')[1].rsplit('"', 1)[0]
        stock_data = data_str.split(',')
        
        # 提取关键字段
        if len(stock_data) < 11:
            logger.error(f"新浪财经API返回数据不完整: {response.text}")
            return None
        
        # 计算涨跌幅和涨跌额
        open_price = float(stock_data[1])
        prev_close = float(stock_data[2])
        current_price = float(stock_data[3])
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100
        
        result = {
            'symbol': symbol,
            'name': stock_data[0],
            'current_price': current_price,
            'open_price': open_price,
            'prev_close': prev_close,
            'high_price': float(stock_data[4]),
            'low_price': float(stock_data[5]),
            'buy_price': float(stock_data[6]),
            'sell_price': float(stock_data[7]),
            'volume': int(stock_data[8]),  # 成交量（手）
            'amount': float(stock_data[9]),  # 成交额（元）
            'change': change,
            'change_percent': change_percent,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'sina_finance'
        }
        
        logger.info(f"成功获取股票 {stock_data[0]}({symbol}) 的实时数据")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"新浪财经API请求失败: {e}")
        return None
    except (IndexError, ValueError, AttributeError) as e:
        logger.error(f"新浪财经API数据解析失败: {e}")
        logger.error(f"原始响应: {response.text}")
        return None


def generate_time_sharing_chart(stock_data: Dict, output_path: str) -> bool:
    """
    生成单只股票的分时股价图
    
    Args:
        stock_data: 包含股票数据的字典
        output_path: 图表保存路径
        
    Returns:
        bool: 图表生成成功返回True，失败返回False
    """
    try:
        # 这里简单模拟分时数据，实际应用中可能需要定时获取多个时间点的数据
        # 创建时间序列（从开盘到当前时间，每5分钟一个点）
        start_time = datetime.datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        end_time = datetime.datetime.now()
        
        # 如果当前时间在开盘前或收盘后，使用模拟时间
        if end_time.time() < datetime.time(9, 30) or end_time.time() > datetime.time(15, 0):
            start_time = datetime.datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
            end_time = start_time.replace(hour=15, minute=0, second=0)
        
        # 生成时间点（每5分钟一个点）
        time_points = pd.date_range(start=start_time, end=end_time, freq='5T')
        
        # 模拟价格数据（围绕当前价格波动）
        import numpy as np
        base_price = stock_data['current_price']
        price_data = base_price + np.random.normal(0, base_price * 0.005, len(time_points))
        
        # 确保开盘价正确
        if len(price_data) > 0:
            price_data[0] = stock_data['open_price']
            # 最后一个价格设为当前价格
            price_data[-1] = stock_data['current_price']
        
        # 创建DataFrame
        df = pd.DataFrame({
            'time': time_points,
            'price': price_data
        })
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制分时线
        ax.plot(df['time'], df['price'], color='#1f77b4', linewidth=2)
        
        # 绘制开盘价水平线
        ax.axhline(y=stock_data['open_price'], color='#ff7f0e', linestyle='--', alpha=0.7, linewidth=1)
        
        # 绘制当前价点
        ax.scatter(df['time'].iloc[-1], df['price'].iloc[-1], color='#2ca02c', s=100, zorder=5)
        
        # 设置标题和标签
        ax.set_title(f'{stock_data["name"]}({stock_data["symbol"]}) 分时图', fontsize=16, fontweight='bold')
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('价格 (元)', fontsize=12)
        
        # 设置时间轴格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.xticks(rotation=45)
        
        # 设置价格轴范围
        price_min = min(df['price']) * 0.998
        price_max = max(df['price']) * 1.002
        ax.set_ylim(price_min, price_max)
        
        # 添加网格线
        ax.grid(True, alpha=0.3)
        
        # 添加数据标签
        current_price = stock_data['current_price']
        change = stock_data['change']
        change_percent = stock_data['change_percent']
        
        # 确定涨跌幅颜色
        color = 'red' if change >= 0 else 'green'
        
        # 添加当前价格和涨跌幅信息
        info_text = f'当前价: {current_price:.2f}元\n'
        info_text += f'涨跌额: {change:+.2f}元\n'
        info_text += f'涨跌幅: {change_percent:+.2f}%'
        
        ax.text(0.02, 0.95, info_text, transform=ax.transAxes, 
                fontsize=12, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"成功生成分时图: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"生成分时图失败: {e}")
        return False


def get_multiple_stocks_data(symbols: List[str]) -> Dict[str, Optional[Dict]]:
    """
    批量获取多只股票的实时数据
    
    Args:
        symbols: 股票代码列表，格式如["sh600519", "sz000001"]
        
    Returns:
        Dict: 以股票代码为键，实时数据为值的字典
    """
    results = {}
    
    # 新浪API支持批量查询，用逗号分隔多个股票代码
    if symbols:
        try:
            # 构造批量查询URL
            symbols_str = ",".join(symbols)
            url = SINA_API_URL.format(symbols_str)
            
            # 发送请求
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            # 解析返回数据
            response_lines = response.text.strip().split(';')
            
            for i, line in enumerate(response_lines):
                if not line.strip():
                    continue
                    
                try:
                    # 提取股票代码和数据
                    # 格式：var hq_str_sh600519="贵州茅台,1700.00,..."
                    symbol_part = line.split('=')[0].split('_')[-1]
                    if symbol_part in symbols:
                        data_str = line.split('="')[1].rsplit('"', 1)[0]
                        stock_data = data_str.split(',')
                        
                        if len(stock_data) < 11:
                            logger.error(f"股票 {symbol_part} 数据不完整")
                            results[symbol_part] = None
                            continue
                        
                        open_price = float(stock_data[1])
                        prev_close = float(stock_data[2])
                        current_price = float(stock_data[3])
                        change = current_price - prev_close
                        change_percent = (change / prev_close) * 100
                        
                        results[symbol_part] = {
                            'symbol': symbol_part,
                            'name': stock_data[0],
                            'current_price': current_price,
                            'open_price': open_price,
                            'prev_close': prev_close,
                            'high_price': float(stock_data[4]),
                            'low_price': float(stock_data[5]),
                            'buy_price': float(stock_data[6]),
                            'sell_price': float(stock_data[7]),
                            'volume': int(stock_data[8]),
                            'amount': float(stock_data[9]),
                            'change': change,
                            'change_percent': change_percent,
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'source': 'sina_finance'
                        }
                        
                except Exception as e:
                    logger.error(f"解析股票 {symbols[i]} 数据失败: {e}")
                    results[symbols[i]] = None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"批量获取股票数据失败: {e}")
            # 单个查询失败的股票，尝试逐个查询
            for symbol in symbols:
                results[symbol] = get_stock_realtime_data(symbol)
    
    return results
