# 工具联动（API调用与来源约束）
import requests
import akshare as ak
import pandas as pd
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timedelta
import json
import os
import time
from .prompt_engine import PromptEngine
from .sina_finance_api import get_stock_realtime_data, generate_time_sharing_chart, get_multiple_stocks_data

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDataAPI:
    def __init__(self, api_keys: Dict[str, Dict] = None, prompt_engine: PromptEngine = None, rag=None):
        """初始化API密钥和配置"""
        self.api_keys = api_keys or {}
        self.akshare_enabled = True  # 默认启用AkShare
        # 初始化PromptEngine，用于生成增强回答
        self.prompt_engine = prompt_engine or PromptEngine(rag=rag)
        self.rag = rag  # 保存RAG模块引用
        
    def analyze_stock_performance(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """分析股票近期表现并提供建议
        
        Args:
            symbol: 股票代码
            days: 分析的天数
            
        Returns:
            Dict: 包含股票表现分析和建议的字典
        """
        try:
            # 计算开始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取历史数据
            historical_data = self.get_historical_data(
                symbol, 
                interval="1d",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            if not historical_data or len(historical_data) < 2:
                return {
                    "performance": None,
                    "analysis": "无法获取足够的历史数据进行分析",
                    "advice": "建议关注后续走势"
                }
            
            # 计算区间表现
            first_close = historical_data[0]['close']
            last_close = historical_data[-1]['close']
            price_change = last_close - first_close
            price_change_percent = (price_change / first_close) * 100
            
            # 计算最高价和最低价
            highs = [data['high'] for data in historical_data]
            lows = [data['low'] for data in historical_data]
            max_price = max(highs)
            min_price = min(lows)
            
            # 计算波动率
            volatility = (max_price - min_price) / first_close * 100
            
            # 计算成交量情况
            volumes = [data['volume'] for data in historical_data]
            avg_volume = sum(volumes) / len(volumes)
            recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else avg_volume
            volume_change = (recent_volume - avg_volume) / avg_volume * 100
            
            # 计算支撑位和阻力位
            support_levels = []
            resistance_levels = []
            
            # 1. 移动平均线作为支撑/阻力位
            closes = [data['close'] for data in historical_data]
            if len(closes) >= 5:
                ma5 = sum(closes[-5:]) / 5
                support_levels.append(round(ma5, 2))
            if len(closes) >= 10:
                ma10 = sum(closes[-10:]) / 10
                support_levels.append(round(ma10, 2))
            if len(closes) >= 20:
                ma20 = sum(closes[-20:]) / 20
                support_levels.append(round(ma20, 2))
            
            # 2. 最近的低点作为支撑位，最近的高点作为阻力位
            recent_lows = sorted(lows[-20:])[:3]  # 最近20天的3个低点
            recent_highs = sorted(highs[-20:], reverse=True)[:3]  # 最近20天的3个高点
            
            support_levels.extend([round(low, 2) for low in recent_lows])
            resistance_levels.extend([round(high, 2) for high in recent_highs])
            
            # 去重并排序
            support_levels = sorted(list(set(support_levels)))
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
            
            # 生成分析和建议
            analysis = []
            advice = []
            
            if price_change_percent > 0:
                analysis.append(f"最近{days}天上涨了{price_change_percent:.2f}%")
                if price_change_percent > 10:
                    analysis.append("表现强劲，涨幅超过10%")
                    if resistance_levels:
                        advice.append(f"关注阻力位{resistance_levels[0]}元，若突破考虑继续持有")
                    else:
                        advice.append("短期可能存在回调风险，建议谨慎持有或部分减仓")
                else:
                    analysis.append("表现稳健")
                    advice.append("建议继续持有，关注后续成交量变化")
            else:
                analysis.append(f"最近{days}天下跌了{-price_change_percent:.2f}%")
                if price_change_percent < -10:
                    analysis.append("跌幅较大，超过10%")
                    if support_levels:
                        advice.append(f"关注支撑位{support_levels[-1]}元，若跌破考虑止损")
                    else:
                        advice.append("建议关注支撑位，若跌破支撑位考虑止损")
                else:
                    analysis.append("回调幅度在合理范围内")
                    advice.append("建议关注基本面变化，等待企稳信号")
            
            if volatility > 20:
                analysis.append("股价波动较大，风险较高")
                advice.append("建议控制仓位，避免追高")
            else:
                analysis.append("股价波动相对稳定")
                if support_levels:
                    advice.append(f"风险可控，可以考虑在支撑位{support_levels[-1]}元附近逢低布局")
                else:
                    advice.append("风险可控，可以考虑逢低布局")
            
            if volume_change > 30:
                analysis.append("近期成交量明显放大")
                advice.append("成交量放大可能预示着行情变化，建议密切关注")
            elif volume_change < -30:
                analysis.append("近期成交量明显萎缩")
                advice.append("成交量萎缩可能意味着缺乏资金关注，建议谨慎")
            
            # 构建表现分析结果
            performance = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "period_days": days,
                "start_price": first_close,
                "end_price": last_close,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "max_price": max_price,
                "min_price": min_price,
                "volatility": volatility,
                "avg_volume": avg_volume,
                "recent_volume": recent_volume,
                "volume_change_percent": volume_change,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels
            }
            
            return {
                "performance": performance,
                "analysis": "，".join(analysis),
                "advice": "。".join(advice)
            }
            
        except Exception as e:
            logger.error(f"分析股票表现失败 {symbol}: {str(e)}")
            return {
                "performance": None,
                "analysis": "股票表现分析失败",
                "advice": "建议结合其他信息进行投资决策"
            }
    
    def get_stock_price(self, symbol: str, time: Optional[datetime] = None) -> Optional[Dict]:
        """获取股票实时价格（优先使用API查询，失败时使用本地缓存），并提供近期表现分析的建议"""
        try:
            # 优先从新浪财经API获取最新数据
            sina_data = self._get_stock_price_sina(symbol)
            if sina_data:
                # 分析近期表现
                performance = self.analyze_stock_performance(symbol)
                sina_data["performance_analysis"] = performance
                return sina_data
            
            # 新浪财经API失败，尝试从AkShare API获取最新数据
            ak_data = self._get_stock_price_akshare(symbol)
            if ak_data:
                # 分析近期表现
                performance = self.analyze_stock_performance(symbol)
                ak_data["performance_analysis"] = performance
                return ak_data
            
            # AkShare失败，尝试使用本地缓存
            cache_data = self._get_stock_price_from_cache(symbol)
            if cache_data:
                # 分析近期表现
                performance = self.analyze_stock_performance(symbol)
                cache_data["performance_analysis"] = performance
                return cache_data
            
            # 缓存获取失败，尝试使用Alpha Vantage
            alpha_data = self._get_stock_price_alpha_vantage(symbol)
            if alpha_data:
                # 分析近期表现
                performance = self.analyze_stock_performance(symbol)
                alpha_data["performance_analysis"] = performance
                return alpha_data
            
            # 都失败了，返回None
            return None
        except Exception as e:
            logger.error(f"获取股票价格失败 {symbol}: {str(e)}")
            return None
    
    def _get_stock_price_sina(self, symbol: str) -> Optional[Dict]:
        """使用新浪财经API获取股票数据"""
        try:
            # 处理股票代码格式，将.SS转换为sh，.SZ转换为sz
            processed_symbol = symbol
            if processed_symbol.endswith('.SS'):
                processed_symbol = 'sh' + processed_symbol[:-3]
            elif processed_symbol.endswith('.SZ'):
                processed_symbol = 'sz' + processed_symbol[:-3]
            
            # 调用新浪财经API获取数据
            sina_data = get_stock_realtime_data(processed_symbol)
            if sina_data:
                # 生成分时图
                chart_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'charts')
                os.makedirs(chart_output_dir, exist_ok=True)
                chart_path = os.path.join(chart_output_dir, f"time_sharing_{symbol.replace('.', '_')}.png")
                generate_time_sharing_chart(sina_data, chart_path)
                
                # 转换数据格式，使其与其他数据源保持一致
                result = {
                    'symbol': symbol,
                    'price': sina_data['current_price'],
                    'change': sina_data['change_percent'],
                    'change_amount': sina_data['change'],
                    'volume': sina_data['volume'],
                    'amount': sina_data['amount'],
                    'high': sina_data['high_price'],
                    'low': sina_data['low_price'],
                    'open': sina_data['open_price'],
                    'prev_close': sina_data['prev_close'],
                    'timestamp': sina_data['timestamp'],
                    'source': sina_data['source'],
                    'time_sharing_chart_path': chart_path
                }
                return result
            return None
        except Exception as e:
            logger.error(f"使用新浪财经API获取股票价格失败 {symbol}: {str(e)}")
            return None
    
    def _get_stock_price_from_cache(self, symbol: str) -> Optional[Dict]:
        """从本地缓存文件获取股票价格（优先CSV缓存，其次JSON缓存）"""
        try:
            # 提取股票代码（处理多种格式：601288.SS, sh601288, 601288）
            stock_code = symbol.split('.')[0]  # 去掉后缀
            # 去掉前缀（如sh, sz）
            if stock_code.startswith('sh') or stock_code.startswith('sz'):
                stock_code = stock_code[2:]
            elif stock_code.startswith('SSE') or stock_code.startswith('SZSE'):
                stock_code = stock_code[3:]
            
            # 步骤1：尝试从stock_data目录下的CSV文件获取
            stock_data_dir = r"D:\code\financial_assistant_agent\stock_data"
            csv_files = [f for f in os.listdir(stock_data_dir) if f.endswith('.csv')]
            if csv_files:
                # 按日期排序，获取最新的CSV文件
                csv_files.sort(reverse=True)
                latest_csv = os.path.join(stock_data_dir, csv_files[0])
                logger.info(f"正在从缓存文件获取股票数据: {latest_csv}")
                
                # 读取CSV文件（使用正确的编码）
                df = pd.read_csv(latest_csv, encoding='utf-8')
                
                # 查找匹配的股票数据（代码列可能是"代码"或"code"）
                code_column = "代码" if "代码" in df.columns else "code" if "code" in df.columns else None
                if code_column:
                    # 确保股票代码列是字符串类型
                    df[code_column] = df[code_column].astype(str)
                    
                    # 匹配股票代码
                    stock_data = df[df[code_column] == stock_code]
                    if not stock_data.empty:
                        # 获取第一行匹配的数据
                        stock_data = stock_data.iloc[0]
                        
                        # 返回完整的数据结构
                        return {
                            'symbol': symbol,
                            'price': float(stock_data["最新价"]),
                            'change': float(stock_data["涨跌幅"]),
                            'change_amount': float(stock_data["涨跌额"]),
                            'volume': int(stock_data["成交量"]),
                            'amount': float(stock_data["成交额"]),
                            'high': float(stock_data["最高"]),
                            'low': float(stock_data["最低"]),
                            'open': float(stock_data["今开"]),
                            'prev_close': float(stock_data["昨收"]),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'source': 'akshare_csv_cache'
                        }
            
            # 步骤2：尝试从cache/stock_data目录下的JSON缓存文件获取
            cache_dir = r"D:\code\financial_assistant_agent\cache\stock_data"
            logger.info(f"尝试从JSON缓存目录获取数据: {cache_dir}")
            
            if not os.path.exists(cache_dir):
                logger.warning(f"JSON缓存目录不存在: {cache_dir}")
                return None
            
            # 查找匹配的JSON缓存文件（如600519.SS_1d.json或sh601288_1d.json）
            json_files = []
            for file in os.listdir(cache_dir):
                if file.endswith('.json'):
                    # 检查文件名是否包含股票代码（可能带或不带前缀/后缀）
                    if stock_code in file or symbol in file:
                        json_files.append(os.path.join(cache_dir, file))
            
            if not json_files:
                logger.warning(f"未找到匹配的JSON缓存文件，股票代码: {stock_code}，原始符号: {symbol}")
                return None
            
            # 按修改时间排序，获取最新的JSON缓存文件
            json_files.sort(key=os.path.getmtime, reverse=True)
            latest_json = json_files[0]
            logger.info(f"正在从JSON缓存文件获取股票数据: {latest_json}")
            
            # 读取JSON缓存文件
            with open(latest_json, 'r', encoding='utf-8') as f:
                historical_data = json.load(f)
            
            if not historical_data:
                logger.warning(f"JSON缓存文件为空: {latest_json}")
                return None
            
            # 按日期排序，获取最新的一条数据
            # 确保日期格式正确，以便排序
            def parse_date(item):
                if 'date' in item:
                    return datetime.strptime(item['date'], '%Y-%m-%d')
                return datetime.min
            
            historical_data.sort(key=parse_date, reverse=True)
            latest_data = historical_data[0]
            
            # 从最新数据中提取所需字段
            # 计算涨跌幅和涨跌额
            close_price = float(latest_data.get('close', 0))
            prev_close = float(latest_data.get('prev_close', close_price))  # 如果没有昨收价，使用收盘价
            change_amount = close_price - prev_close
            change_percent = (change_amount / prev_close) * 100 if prev_close != 0 else 0
            
            # 返回完整的数据结构
            return {
                'symbol': symbol,
                'price': close_price,
                'change': change_percent,
                'change_amount': change_amount,
                'volume': int(latest_data.get('volume', 0)),
                'amount': float(latest_data.get('amount', 0)),
                'high': float(latest_data.get('high', 0)),
                'low': float(latest_data.get('low', 0)),
                'open': float(latest_data.get('open', 0)),
                'prev_close': prev_close,
                'timestamp': latest_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'source': 'akshare_json_cache'
            }
            
        except Exception as e:
            logger.error(f"从缓存获取股票价格失败 {symbol}: {str(e)}")
            return None

    def _get_stock_price_akshare(self, symbol: str) -> Optional[Dict]:
        """使用AkShare获取股票数据"""
        try:
            # 检查是否是ETF查询（通过股票名称或代码判断）
            is_etf_query = False
            # 如果symbol不是标准的股票代码格式（如"黄金etf"），可能是ETF查询
            if not (symbol.endswith('.SS') or symbol.endswith('.SZ') or symbol.endswith('.HK') or symbol.endswith('.US')):
                is_etf_query = True
                etf_name = symbol
            
            if symbol.endswith('.SS') or symbol.endswith('.SZ'):
                # A股数据或ETF数据
                stock_code = symbol.replace('.SS', '').replace('.SZ', '')
                # 去掉前缀（如sh, sz）
                if stock_code.startswith('sh') or stock_code.startswith('sz'):
                    stock_code = stock_code[2:]
                elif stock_code.startswith('SSE') or stock_code.startswith('SZSE'):
                    stock_code = stock_code[3:]
                
                # 检查是否是ETF代码
                # 5开头的6位数字可能是ETF（深圳市场）
                if len(stock_code) == 6 and (stock_code.startswith('5') or stock_code.startswith('15') or stock_code.startswith('51')):
                    is_etf_query = True
                    etf_code = stock_code
                else:
                    # 步骤1：检查是否有当天的缓存文件且不超过30分钟
                    today = datetime.now().strftime('%Y%m%d')
                    cache_file = f"stock_data/akshare_stock_data_{today}.csv"
                    
                    use_cache = False
                    if os.path.exists(cache_file):
                        # 检查缓存文件的修改时间
                        file_time = os.path.getmtime(cache_file)
                        current_time = time.time()
                        # 如果缓存文件不超过30分钟，使用缓存
                        if (current_time - file_time) < 1800:  # 30分钟 = 1800秒
                            logger.info(f"使用当天缓存文件: {cache_file}")
                            # 从缓存文件读取数据
                            data = pd.read_csv(cache_file)
                            use_cache = True
                        else:
                            logger.info(f"缓存文件超过30分钟，重新获取数据: {cache_file}")
                    
                    if not use_cache:
                        logger.info("没有有效缓存文件，调用AkShare API获取数据")
                        # 调用API获取数据
                        data = ak.stock_zh_a_spot_em()
                        # 保存为当天的缓存文件
                        data.to_csv(cache_file, index=False, encoding='utf-8')
                        logger.info(f"已保存当天数据到缓存文件: {cache_file}")
                        
                    stock_data = data[data['代码'] == stock_code]
                    
                    if not stock_data.empty:
                        # 获取数据行
                        row = stock_data.iloc[0]
                        
                        # 构建返回结果，使用try-except处理可能缺失的字段
                        result = {
                            'symbol': symbol,
                            'price': float(row['最新价']),
                            'change': float(row['涨跌幅']),
                            'change_amount': float(row['涨跌额']),
                            'volume': int(row['成交量']),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'source': 'akshare_daily_cache' if use_cache else 'akshare'
                        }
                        
                        # 尝试获取其他可选字段
                        try:
                            result['amount'] = float(row['成交额'])
                        except (KeyError, ValueError, TypeError):
                            result['amount'] = 0.0
                            
                        try:
                            result['high'] = float(row['最高价'] if '最高价' in row else row['最高'])
                        except (KeyError, ValueError, TypeError):
                            result['high'] = float(row['最新价'])
                            
                        try:
                            result['low'] = float(row['最低价'] if '最低价' in row else row['最低'])
                        except (KeyError, ValueError, TypeError):
                            result['low'] = float(row['最新价'])
                            
                        try:
                            result['open'] = float(row['今开'])
                        except (KeyError, ValueError, TypeError):
                            result['open'] = float(row['最新价'])
                            
                        try:
                            result['prev_close'] = float(row['昨收'])
                        except (KeyError, ValueError, TypeError):
                            result['prev_close'] = float(row['最新价'])
                        
                        return result
            
            # 处理ETF查询
            if is_etf_query:
                logger.info(f"处理ETF查询: {symbol}")
                
                # 步骤1：检查是否有当天的ETF缓存文件且不超过30分钟
                today = datetime.now().strftime('%Y%m%d')
                etf_cache_file = f"stock_data/akshare_etf_data_{today}.csv"
                
                use_cache = False
                if os.path.exists(etf_cache_file):
                    # 检查缓存文件的修改时间
                    file_time = os.path.getmtime(etf_cache_file)
                    current_time = time.time()
                    # 如果缓存文件不超过30分钟，使用缓存
                    if (current_time - file_time) < 1800:  # 30分钟 = 1800秒
                        logger.info(f"使用当天ETF缓存文件: {etf_cache_file}")
                        # 从缓存文件读取数据
                        etf_data = pd.read_csv(etf_cache_file)
                        use_cache = True
                    else:
                        logger.info(f"ETF缓存文件超过30分钟，重新获取数据: {etf_cache_file}")
                
                if not use_cache:
                    logger.info("没有有效ETF缓存文件，调用AkShare API获取数据")
                    # 调用API获取ETF数据
                    etf_data = ak.fund_etf_spot_em()
                    # 保存为当天的缓存文件
                    etf_data.to_csv(etf_cache_file, index=False, encoding='utf-8')
                    logger.info(f"已保存当天ETF数据到缓存文件: {etf_cache_file}")
                
                # 查询ETF数据
                if 'etf_name' in locals():
                    # 通过名称查询ETF
                    etf_result = etf_data[etf_data['名称'].str.contains(etf_name, na=False)]
                    if not etf_result.empty:
                        # 获取第一只匹配的ETF
                        row = etf_result.iloc[0]
                else:
                    # 通过代码查询ETF
                    etf_result = etf_data[etf_data['代码'] == etf_code]
                    if not etf_result.empty:
                        row = etf_result.iloc[0]
                
                if not etf_result.empty:
                    # 构建返回结果，使用try-except处理可能缺失的字段
                    result = {
                        'symbol': symbol,
                        'price': float(row['最新价']),
                        'change': float(row['涨跌幅']),
                        'change_amount': float(row['涨跌额']),
                        'volume': int(row['成交量']),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'akshare_etf_cache' if use_cache else 'akshare_etf'
                    }
                    
                    # 尝试获取其他可选字段
                    try:
                        result['amount'] = float(row['成交额'])
                    except (KeyError, ValueError, TypeError):
                        result['amount'] = 0.0
                        
                    try:
                        result['high'] = float(row['最高价'] if '最高价' in row else row['最高'])
                    except (KeyError, ValueError, TypeError):
                        result['high'] = float(row['最新价'])
                        
                    try:
                        result['low'] = float(row['最低价'] if '最低价' in row else row['最低'])
                    except (KeyError, ValueError, TypeError):
                        result['low'] = float(row['最新价'])
                        
                    try:
                        result['open'] = float(row['开盘价'])
                    except (KeyError, ValueError, TypeError):
                        result['open'] = float(row['最新价'])
                        
                    try:
                        result['prev_close'] = float(row[' 昨收'])
                    except (KeyError, ValueError, TypeError):
                        result['prev_close'] = float(row['最新价'])
                    
                    return result
                    
            elif symbol.endswith('.HK'):
                # 港股数据
                stock_code = symbol.replace('.HK', '')
                
                # 步骤1：检查是否有当天的缓存文件
                today = datetime.now().strftime('%Y%m%d')
                cache_file = f"stock_data/akshare_hk_stock_data_{today}.csv"
                
                if os.path.exists(cache_file):
                    logger.info(f"使用当天港股缓存文件: {cache_file}")
                    # 从缓存文件读取数据
                    data = pd.read_csv(cache_file)
                else:
                    logger.info("没有当天港股缓存文件，调用AkShare API获取数据")
                    # 调用API获取数据
                    data = ak.stock_hk_spot_em()
                    # 保存为当天的缓存文件
                    data.to_csv(cache_file, index=False, encoding='utf-8')
                    logger.info(f"已保存当天港股数据到缓存文件: {cache_file}")
                
                stock_data = data[data['代码'] == stock_code]
                
                if not stock_data.empty:
                    # 获取数据行
                    row = stock_data.iloc[0]
                    
                    result = {
                        'symbol': symbol,
                        'price': float(row['最新价']),
                        'change': float(row['涨跌幅']),
                        'change_amount': float(row['涨跌额']),
                        'volume': int(row['成交量']),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'akshare' if not os.path.exists(cache_file) else 'akshare_daily_cache'
                    }
                    
                    # 尝试获取其他可选字段
                    try:
                        result['amount'] = float(row['成交额'])
                    except (KeyError, ValueError, TypeError):
                        result['amount'] = 0.0
                        
                    return result
                    
        except Exception as e:
            logger.error(f"使用AkShare获取股票价格失败 {symbol}: {str(e)}")
            return None

    def _get_stock_price_alpha_vantage(self, symbol: str) -> Optional[Dict]:
        """使用Alpha Vantage获取股票数据（主要美股）"""
        try:
            if not self.api_keys.get("alpha_vantage"):
                return None
                
            alpha_config = self.api_keys["alpha_vantage"]
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol.replace('.US', ''),
                "apikey": alpha_config["api_key"]
            }
            
            response = requests.get(alpha_config["base_url"], params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "Global Quote" in data:
                quote = data["Global Quote"]
                return {
                    'symbol': symbol,
                    'price': float(quote.get("05. price", 0)),
                    'change': float(quote.get("10. change percent", "0%").replace('%', '')),
                    'change_amount': float(quote.get("09. change", 0)),
                    'volume': int(quote.get("06. volume", 0)),
                    'timestamp': quote.get("07. latest trading day", ""),
                    'source': 'alpha_vantage'
                }
                
        except Exception as e:
            logger.warning(f"Alpha Vantage获取股票数据失败: {e}")
            
        return None
    
    def generate_stock_time_sharing_chart(self, symbol: str, output_path: str) -> bool:
        """
        生成单只股票的分时股价图
        
        Args:
            symbol: 股票代码，格式如"sh600519"（上证）或"sz000001"（深证）
            output_path: 图表保存路径
            
        Returns:
            bool: 图表生成成功返回True，失败返回False
        """
        try:
            # 处理股票代码格式，将.SS转换为sh，.SZ转换为sz
            processed_symbol = symbol
            if processed_symbol.endswith('.SS'):
                processed_symbol = 'sh' + processed_symbol[:-3]
            elif processed_symbol.endswith('.SZ'):
                processed_symbol = 'sz' + processed_symbol[:-3]
            
            # 获取股票实时数据
            stock_data = get_stock_realtime_data(processed_symbol)
            if not stock_data:
                logger.error(f"获取股票{symbol}数据失败，无法生成分时图")
                return False
            
            # 生成分时图
            return generate_time_sharing_chart(stock_data, output_path)
        except Exception as e:
            logger.error(f"生成分时图失败 {symbol}: {str(e)}")
            return False

    def get_market_index(self, index_name: str, time: Optional[datetime] = None) -> Optional[Dict]:
        """获取市场指数数据（优先使用AkShare）"""
        try:
            # 使用AkShare获取A股指数
            akshare_result = self._get_market_index_akshare(index_name)
            if akshare_result:
                return akshare_result
                
            # 备用方案：TwelveData
            return self._get_market_index_twelvedata(index_name)
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return None

    def _get_market_index_akshare(self, index_name: str) -> Optional[Dict]:
        """使用AkShare获取指数数据"""
        try:
            # 获取A股指数实时数据
            data = ak.stock_zh_index_spot()
            
            # 指数代码映射
            index_mapping = {
                '上证指数': '000001',
                '深证成指': '399001',
                '创业板指': '399006',
                '沪深300': '000300',
                '上证50': '000016'
            }
            
            if index_name in index_mapping:
                index_code = index_mapping[index_name]
                index_data = data[data['代码'] == index_code]
                
                if not index_data.empty:
                    return {
                        'name': index_name,
                        'price': float(index_data.iloc[0]['最新价']),
                        'change': float(index_data.iloc[0]['涨跌幅']),
                        'change_amount': float(index_data.iloc[0]['涨跌额']),
                        'volume': int(index_data.iloc[0]['成交量']),
                        'amount': float(index_data.iloc[0]['成交额']),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'akshare'
                    }
                    
        except Exception as e:
            logger.warning(f"AkShare获取指数数据失败: {e}")
            
        return None

    def _get_market_index_twelvedata(self, index_name: str) -> Optional[Dict]:
        """使用TwelveData获取指数数据"""
        try:
            if not self.api_keys.get("twelvedata"):
                return None
                
            twelve_config = self.api_keys["twelvedata"]
            params = {
                "symbol": index_name,
                "apikey": twelve_config["api_key"]
            }
            
            response = requests.get(f"{twelve_config['base_url']}/price", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"TwelveData获取指数数据失败: {e}")
            return None

    def get_financial_news(self, query: str = "", limit: int = 10) -> Optional[Dict]:
        """获取财经新闻（多数据源）"""
        try:
            # 优先使用AkShare获取财经新闻
            akshare_news = self._get_news_akshare(limit)
            
            # 备用：NewsAPI
            newsapi_news = self._get_news_newsapi(query, limit)
            
            # 合并结果
            all_articles = []
            if akshare_news and 'articles' in akshare_news:
                all_articles.extend(akshare_news['articles'])
            if newsapi_news and 'articles' in newsapi_news:
                all_articles.extend(newsapi_news['articles'])
                
            return {
                'articles': all_articles[:limit],
                'total': len(all_articles),
                'timestamp': datetime.now().isoformat(),
                'sources': ['akshare', 'newsapi']
            }
            
        except Exception as e:
            logger.error(f"获取新闻数据失败: {e}")
            return None

    def _get_news_akshare(self, limit: int = 10) -> Optional[Dict]:
        """使用AkShare获取财经新闻"""
        try:
            # 获取财经新闻
            news_data = ak.news_roll()
            
            articles = []
            for index, row in news_data.head(limit).iterrows():
                article = {
                    'title': row['新闻标题'],
                    'description': row['新闻内容'][:200] + '...' if len(str(row['新闻内容'])) > 200 else str(row['新闻内容']),
                    'source': row['新闻来源'],
                    'publishedAt': row['发布时间'],
                    'url': row['新闻链接']
                }
                articles.append(article)
                
            return {'articles': articles}
            
        except Exception as e:
            logger.warning(f"AkShare获取新闻失败: {e}")
            return None

    def _get_news_newsapi(self, query: str = "", limit: int = 5) -> Optional[Dict]:
        """使用NewsAPI获取财经新闻"""
        try:
            if not self.api_keys.get("newsapi"):
                return None
                
            news_config = self.api_keys["newsapi"]
            params = {
                "q": query or "财经 股票 经济",
                "language": "zh",
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": news_config["api_key"]
            }
            
            response = requests.get(f"{news_config['base_url']}/everything", params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"NewsAPI获取新闻失败: {e}")
            return None

    def get_today_market_summary(self) -> Optional[Dict]:
        """获取今日市场概况"""
        try:
            summary = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'major_indices': {},
                'market_activity': {},
                'hot_sectors': []
            }
            
            # 获取主要指数
            indices = ['上证指数', '深证成指', '创业板指', '沪深300']
            for index in indices:
                index_data = self.get_market_index(index)
                if index_data:
                    summary['major_indices'][index] = index_data
            
            # 获取市场活跃度
            try:
                market_activity = ak.stock_market_activity()
                summary['market_activity'] = {
                    'total_companies': market_activity.get('总数', 'N/A'),
                    'rising_companies': market_activity.get('上涨家数', 'N/A'),
                    'falling_companies': market_activity.get('下跌家数', 'N/A'),
                    'unchanged_companies': market_activity.get('平盘家数', 'N/A')
                }
            except Exception as e:
                logger.warning(f"获取市场活跃度失败: {e}")
            
            # 获取热门板块
            try:
                hot_sectors = ak.stock_board_concept_spot_em()
                summary['hot_sectors'] = hot_sectors.head(5).to_dict('records')
            except Exception as e:
                logger.warning(f"获取热门板块失败: {e}")
            
            return summary
            
        except Exception as e:
            logger.error(f"获取市场概况失败: {e}")
            return None

    def get_stock_intraday(self, symbol: str, interval: str = "5min") -> Optional[Dict]:
        """获取股票日内数据"""
        try:
            # 优先使用AkShare
            if symbol.endswith('.SS') or symbol.endswith('.SZ'):
                stock_code = symbol.replace('.SS', '').replace('.SZ', '')
                data = ak.stock_zh_a_hist_min_em(symbol=stock_code, period=interval)
                
                if not data.empty:
                    return {
                        'symbol': symbol,
                        'data': data.to_dict('records'),
                        'interval': interval,
                        'source': 'akshare'
                    }
                    
            # 备用：Alpha Vantage
            return self._get_stock_intraday_alpha_vantage(symbol, interval)
            
        except Exception as e:
            logger.error(f"获取股票日内数据失败: {e}")
            return None

    def _get_stock_intraday_alpha_vantage(self, symbol: str, interval: str) -> Optional[Dict]:
        """使用Alpha Vantage获取日内数据"""
        try:
            if not self.api_keys.get("alpha_vantage"):
                return None
                
            alpha_config = self.api_keys["alpha_vantage"]
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol.replace('.US', ''),
                "interval": interval,
                "apikey": alpha_config["api_key"]
            }
            
            response = requests.get(alpha_config["base_url"], params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Alpha Vantage获取日内数据失败: {e}")
            return None

    def get_economic_data(self, indicator: str = "GDP") -> Optional[Dict]:
        """获取经济数据"""
        try:
            # 使用AkShare获取宏观经济数据
            if indicator == "GDP":
                data = ak.macro_china_gdp()
            elif indicator == "CPI":
                data = ak.macro_china_cpi()
            elif indicator == "PPI":
                data = ak.macro_china_ppi()
            else:
                return None
                
            return {
                'indicator': indicator,
                'data': data.to_dict('records'),
                'source': 'akshare',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取经济数据失败: {e}")
            return None

    def get_historical_data(self, symbol: str, interval: str = "1d", start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """获取股票或ETF历史数据（支持缓存）"""
        try:
            # 处理股票代码格式：先去掉后缀，再去掉前缀
            stock_code = symbol.split('.')[0]  # 去掉后缀（如.SS, .SZ, .HK）
            # 去掉前缀（如sh, sz）
            if stock_code.startswith('sh') or stock_code.startswith('sz'):
                stock_code = stock_code[2:]
            elif stock_code.startswith('SSE') or stock_code.startswith('SZSE'):
                stock_code = stock_code[3:]
            logger.info(f"正在处理股票代码: {symbol}，处理后: {stock_code}")
            
            # 判断是否为ETF（以51、15、58开头的6位数字）
            is_etf = False
            if len(stock_code) == 6 and stock_code.isdigit():
                if stock_code.startswith(('51', '15', '58')):
                    is_etf = True
                    logger.info(f"识别为ETF: {stock_code}")
            
            # 设置缓存目录和文件名
            cache_dir = r"D:\code\financial_assistant_agent\cache\stock_data"
            cache_file = os.path.join(cache_dir, f"{symbol}_{interval}.json")
            logger.info(f"缓存目录: {cache_dir}，缓存文件: {cache_file}")
            
            # 创建缓存目录
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
                logger.info(f"创建缓存目录: {cache_dir}")
            
            # 检查缓存是否有效（7天有效期）
            cache_valid = False
            if os.path.exists(cache_file):
                cache_time = os.path.getmtime(cache_file)
                if time.time() - cache_time < 7 * 24 * 3600:
                    cache_valid = True
                    logger.info(f"缓存有效，将加载缓存数据")
            
            # 加载缓存数据
            cached_data = []
            if cache_valid:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                    
                    # 处理不同的缓存格式
                    data_list = []
                    if isinstance(loaded_data, list):
                        data_list = loaded_data
                    elif isinstance(loaded_data, dict) and 'data' in loaded_data:
                        data_list = loaded_data['data']
                    else:
                        logger.error(f"缓存数据格式错误: {type(loaded_data)}")
                        cache_valid = False
                        data_list = []
                    
                    # 映射中文键名到英文键名
                    field_mapping = {
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '涨跌幅': 'change',
                        '股票代码': 'stock_code'
                    }
                    
                    # 转换数据格式
                    for item in data_list:
                        # 检查是否已经是英文键名格式
                        if 'date' in item:
                            cached_data.append(item)
                        else:
                            # 转换中文键名为英文
                            new_item = {}
                            for cn_key, en_key in field_mapping.items():
                                if cn_key in item:
                                    new_item[en_key] = item[cn_key]
                            # 添加symbol字段
                            new_item['symbol'] = symbol
                            cached_data.append(new_item)
                    
                    logger.info(f"从缓存加载了 {len(cached_data)} 条历史数据")
                    
                    # 如果指定了日期范围，过滤数据
                    if start_date and end_date:
                        filtered_data = []
                        for item in cached_data:
                            if 'date' in item and start_date <= item['date'] <= end_date:
                                filtered_data.append(item)
                        logger.info(f"按日期范围过滤后剩余 {len(filtered_data)} 条数据")
                        return filtered_data
                    elif start_date:
                        filtered_data = []
                        for item in cached_data:
                            if 'date' in item and item['date'] >= start_date:
                                filtered_data.append(item)
                        logger.info(f"按起始日期过滤后剩余 {len(filtered_data)} 条数据")
                        return filtered_data
                    elif end_date:
                        filtered_data = []
                        for item in cached_data:
                            if 'date' in item and item['date'] <= end_date:
                                filtered_data.append(item)
                        logger.info(f"按结束日期过滤后剩余 {len(filtered_data)} 条数据")
                        return filtered_data
                    return cached_data
                except Exception as e:
                    logger.error(f"加载缓存数据失败: {e}")
                    cache_valid = False
            
            # 缓存无效或不存在，从API获取新数据
            logger.info(f"缓存无效或不存在，开始从API获取新数据")
            
            # AkShare周期映射
            period_map = {
                "1d": "daily",
                "1w": "weekly",
                "1mo": "monthly"
            }
            ak_period = period_map.get(interval, "daily")
            logger.info(f"时间周期映射: {interval} -> {ak_period}")
            
            # 获取历史数据
            data = None
            if is_etf:
                # ETF数据
                logger.info(f"正在获取ETF {stock_code} 的历史数据")
                try:
                    if start_date and end_date:
                        data = ak.fund_etf_hist_em(symbol=stock_code, period=ak_period, start_date=start_date, end_date=end_date)
                    elif not start_date and not end_date:
                        # 未指定时间范围，获取所有历史数据
                        data = ak.fund_etf_hist_em(symbol=stock_code, period=ak_period)
                    logger.info(f"ETF数据列名: {data.columns.tolist()}")
                except Exception as e:
                    logger.error(f"获取ETF数据失败: {e}")
            else:
                # 股票数据
                logger.info(f"正在获取股票 {stock_code} 的历史数据")
                try:
                    if symbol.endswith('.SS') or symbol.endswith('.SZ'):
                        # A股数据
                        logger.info(f"获取A股 {stock_code} 的 {ak_period} 数据")
                        if start_date and end_date:
                            data = ak.stock_zh_a_hist(symbol=stock_code, period=ak_period, start_date=start_date, end_date=end_date)
                        else:
                            # 未指定时间范围，获取所有历史数据
                            data = ak.stock_zh_a_hist(symbol=stock_code, period=ak_period)
                        logger.info(f"A股数据列名: {data.columns.tolist()}")
                        logger.info(f"A股数据前5行: {data.head()}")
                    elif symbol.endswith('.HK'):
                        # 港股数据
                        logger.info(f"获取港股 {stock_code} 的历史数据")
                        try:
                            if start_date and end_date:
                                data = ak.stock_hk_hist(symbol=stock_code, period=ak_period, start_date=start_date, end_date=end_date)
                            else:
                                # 未指定时间范围，获取所有历史数据
                                data = ak.stock_hk_hist(symbol=stock_code, period=ak_period)
                            logger.info(f"港股数据列名: {data.columns.tolist()}")
                        except Exception as e:
                            logger.error(f"港股API调用失败: {e}")
                            return []
                except Exception as e:
                    logger.error(f"获取股票数据失败: {e}")
            
            logger.info(f"获取到数据形状: {data.shape if data is not None else 'None'}")
            
            if data is not None and not data.empty:
                # 转换数据格式
                historical_data = []
                
                # ETF数据字段映射 - 适配不同的字段名
                if is_etf:
                    for _, row in data.iterrows():
                        # 尝试多种字段名组合
                        open_col = row.get('开盘价', row.get('开盘', 0))
                        high_col = row.get('最高价', row.get('最高', 0))
                        low_col = row.get('最低价', row.get('最低', 0))
                        close_col = row.get('收盘价', row.get('收盘', 0))
                        volume_col = row.get('成交量', row.get('成交', 0))
                        amount_col = row.get('成交额', row.get('金额', 0))
                        change_col = row.get('涨跌幅', row.get('涨跌', 0))
                        
                        # 处理日期字段
                        date_value = row.get('日期', '')
                        if hasattr(date_value, 'strftime'):
                            date_str = date_value.strftime('%Y-%m-%d')
                        else:
                            date_str = str(date_value)
                        
                        historical_data.append({
                            'date': date_str,
                            'open': float(open_col),
                            'high': float(high_col),
                            'low': float(low_col),
                            'close': float(close_col),
                            'volume': int(volume_col) if volume_col != '-' else 0,
                            'amount': float(amount_col) if amount_col != '-' else 0,
                            'change': float(change_col) if change_col != '-' else 0,
                            'symbol': symbol
                        })
                # 股票数据字段映射
                else:
                    for _, row in data.iterrows():
                        # 处理日期字段
                        date_value = row.get('日期', '')
                        if hasattr(date_value, 'strftime'):
                            date_str = date_value.strftime('%Y-%m-%d')
                        else:
                            date_str = str(date_value)
                        
                        historical_data.append({
                            'date': date_str,
                            'open': float(row.get('开盘', 0)),
                            'high': float(row.get('最高', 0)),
                            'low': float(row.get('最低', 0)),
                            'close': float(row.get('收盘', 0)),
                            'volume': int(row.get('成交量', 0)),
                            'amount': float(row.get('成交额', 0)),
                            'change': float(row.get('涨跌幅', 0)),
                            'symbol': symbol
                        })
                
                logger.info(f"转换后获取到 {len(historical_data)} 条历史数据")
                
                # 保存到缓存
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(historical_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"历史数据已保存到缓存: {cache_file}")
                except Exception as e:
                    logger.error(f"保存缓存失败: {e}")
                
                return historical_data
            else:
                logger.warning(f"未获取到历史数据: {symbol}")
                return []
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}", exc_info=True)
            return None
    
    def generate_enhanced_response(self, query: str, history: List[tuple] = None, 
                                  data: Dict = None, intent_analysis: Dict = None) -> Dict:
        """生成增强的自然语言回答
        
        Args:
            query: 用户查询
            history: 对话历史
            data: 数据上下文（如股票价格、市场指数等）
            intent_analysis: 意图分析结果
            
        Returns:
            Dict: 包含生成的回答和相关信息的字典
        """
        try:
            # 准备数据上下文
            data_sources = {
                'real_time_data': data or {}
            }
            
            # 使用PromptEngine构建提示词
            prompt = self.prompt_engine.construct_prompt(
                query=query,
                history=history or [],
                data_sources=data_sources,
                intent_analysis=intent_analysis or {}
            )
            
            # 使用RAG生成增强回答（如果可用）
            rag_result = self.prompt_engine.generate_with_rag(
                query=query,
                history=history or [],
                data_sources=data_sources,
                intent_analysis=intent_analysis or {}
            )
            
            # 合并结果
            result = {
                'prompt': rag_result.get('prompt', prompt),
                'has_rag_context': rag_result.get('has_rag_context', False)
            }
            
            # 如果有RAG源文档，添加到结果中
            if rag_result.get('source_documents'):
                result['source_documents'] = rag_result['source_documents']
            
            return result
            
        except Exception as e:
            logger.error(f"生成增强回答失败: {str(e)}")
            return {
                'error': str(e),
                'prompt': None,
                'has_rag_context': False
            }


# 辅助函数部分
def add_source_citations(response: str, sources: List[Dict], kb) -> str:
    """为回答添加来源引用标注"""
    if not sources:
        return response

    # 提取来源信息
    source_info = []
    for i, source in enumerate(sources, 1):
        # 处理知识库来源
        if hasattr(source, 'get') and source.get('document_id'):
            doc_id = source.get("document_id")
            url = kb.get_url_from_doc_id(doc_id) if hasattr(kb, 'get_url_from_doc_id') else f"文档ID: {doc_id}"
            source_info.append(f"[{i}] 知识库: {url}")
        
        # 处理API数据来源
        elif hasattr(source, 'get') and source.get('source'):
            source_type = source.get('source', '未知来源')
            timestamp = source.get('timestamp', '')
            source_info.append(f"[{i}] {source_type}数据: {timestamp}")

    # 添加引用标注
    if source_info:
        citation_text = "\n\n📚 数据来源:\n" + "\n".join(source_info)
        return response + citation_text
    
    return response


# 新增工具函数
def validate_api_keys(api_keys: Dict) -> Dict:
    """验证API密钥有效性"""
    valid_keys = {}
    
    for api_name, config in api_keys.items():
        if config.get('api_key') and config.get('api_key') != 'your_api_key_here':
            valid_keys[api_name] = config
        else:
            logger.warning(f"{api_name} API密钥未配置或使用默认值")
    
    return valid_keys


def format_financial_data(data: Dict, data_type: str) -> str:
    """格式化金融数据用于显示"""
    if not data:
        return "暂无数据"
    
    try:
        if data_type == "stock":
            return f"""📊 股票数据: {data.get('symbol', 'N/A')}
💰 当前价格: {data.get('price', 'N/A')} 
📈 涨跌幅: {data.get('change', 'N/A')}%
📊 成交量: {data.get('volume', 'N/A')}
⏰ 更新时间: {data.get('timestamp', 'N/A')}"""
        
        elif data_type == "market":
            return f"""🏦 市场概况
主要指数表现:
{chr(10).join([f"- {name}: {info.get('price', 'N/A')} ({info.get('change', 'N/A')}%)" 
               for name, info in data.get('major_indices', {}).items()])}"""
        
        elif data_type == "news":
            articles = data.get('articles', [])
            return f"""📰 最新财经新闻 ({len(articles)}条)
{chr(10).join([f'{i+1}. {article.get("title", "N/A")}' 
               for i, article in enumerate(articles[:3])])}"""
    
    except Exception as e:
        logger.error(f"格式化数据失败: {e}")
    
    return "数据格式异常"


# 使用示例
if __name__ == "__main__":
    # 测试AkShare功能
    api = FinancialDataAPI()
    
    # 测试A股数据
    stock_data = api.get_stock_price("600519.SS")
    print("贵州茅台数据:", stock_data)
    
    # 测试指数数据
    index_data = api.get_market_index("上证指数")
    print("上证指数数据:", index_data)
    
    # 测试新闻数据
    news_data = api.get_financial_news("财经", 5)
    print("财经新闻:", news_data)
    
    # 测试生成增强回答功能
    print("\n=== 测试增强回答功能 ===")
    query = "贵州茅台的最新价格是多少？"
    history = [
        ("你好，我想了解一些股票信息", "你好！我是金融助手，有什么可以帮您？")
    ]
    
    # 生成增强回答
    enhanced_response = api.generate_enhanced_response(
        query=query,
        history=history,
        data={"stock_price": stock_data},
        intent_analysis={"primary_intent": "specific_stock"}
    )
    
    print(f"生成的提示词:\n{enhanced_response['prompt']}")
    print(f"是否使用RAG: {enhanced_response['has_rag_context']}")