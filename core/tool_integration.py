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

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDataAPI:
    def __init__(self, api_keys: Dict[str, Dict] = None):
        """初始化API密钥和配置"""
        self.api_keys = api_keys or {}
        self.akshare_enabled = True  # 默认启用AkShare
        
    def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """获取股票实时价格（优先使用AkShare）"""
        try:
            # 优先使用AkShare获取A股、港股数据
            akshare_result = self._get_stock_price_akshare(symbol)
            if akshare_result:
                return akshare_result
                
            # AkShare失败时使用Alpha Vantage（美股等）
            return self._get_stock_price_alpha_vantage(symbol)
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            return None

    def _get_stock_price_akshare(self, symbol: str) -> Optional[Dict]:
        """使用AkShare获取股票数据"""
        try:
            if symbol.endswith('.SS') or symbol.endswith('.SZ'):
                # A股数据
                stock_code = symbol.replace('.SS', '').replace('.SZ', '')
                data = ak.stock_zh_a_spot_em()
                stock_data = data[data['代码'] == stock_code]
                
                if not stock_data.empty:
                    return {
                        'symbol': symbol,
                        'price': float(stock_data.iloc[0]['最新价']),
                        'change': float(stock_data.iloc[0]['涨跌幅']),
                        'change_amount': float(stock_data.iloc[0]['涨跌额']),
                        'volume': int(stock_data.iloc[0]['成交量']),
                        'amount': float(stock_data.iloc[0]['成交额']),
                        'high': float(stock_data.iloc[0]['最高价']),
                        'low': float(stock_data.iloc[0]['最低价']),
                        'open': float(stock_data.iloc[0]['今开']),
                        'prev_close': float(stock_data.iloc[0]['昨收']),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'akshare'
                    }
                    
            elif symbol.endswith('.HK'):
                # 港股数据
                stock_code = symbol.replace('.HK', '')
                data = ak.stock_hk_spot_em()
                stock_data = data[data['代码'] == stock_code]
                
                if not stock_data.empty:
                    return {
                        'symbol': symbol,
                        'price': float(stock_data.iloc[0]['最新价']),
                        'change': float(stock_data.iloc[0]['涨跌幅']),
                        'volume': int(stock_data.iloc[0]['成交量']),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'akshare'
                    }
                    
        except Exception as e:
            logger.warning(f"AkShare获取股票数据失败 {symbol}: {e}")
            
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

    def get_market_index(self, index_name: str) -> Optional[Dict]:
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
            # 处理股票代码格式
            stock_code = symbol.replace('.SS', '').replace('.SZ', '').replace('.HK', '')
            logger.info(f"正在处理股票代码: {symbol}，处理后: {stock_code}")
            
            # 判断是否为ETF（以51、15、58开头的6位数字）
            is_etf = False
            if len(stock_code) == 6 and stock_code.isdigit():
                if stock_code.startswith(('51', '15', '58')):
                    is_etf = True
                    logger.info(f"识别为ETF: {stock_code}")
            
            # 设置缓存目录和文件名
            cache_dir = "../cache/stock_data"
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
                        cached_data = json.load(f)
                    logger.info(f"从缓存加载了 {len(cached_data)} 条历史数据")
                    
                    # 如果指定了日期范围，过滤数据
                    if start_date and end_date:
                        filtered_data = []
                        for item in cached_data:
                            if start_date <= item['date'] <= end_date:
                                filtered_data.append(item)
                        logger.info(f"按日期范围过滤后剩余 {len(filtered_data)} 条数据")
                        return filtered_data
                    elif start_date:
                        filtered_data = []
                        for item in cached_data:
                            if item['date'] >= start_date:
                                filtered_data.append(item)
                        logger.info(f"按起始日期过滤后剩余 {len(filtered_data)} 条数据")
                        return filtered_data
                    elif end_date:
                        filtered_data = []
                        for item in cached_data:
                            if item['date'] <= end_date:
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
                        logger.info(f"获取A股 {stock_code} 的 {ak_period} 数据，时间范围: {start_date} 至 {end_date}")
                        data = ak.stock_zh_a_hist(symbol=stock_code, period=ak_period)
                        logger.info(f"A股数据列名: {data.columns.tolist()}")
                        logger.info(f"A股数据前5行: {data.head()}")
                    elif symbol.endswith('.HK'):
                        # 港股数据
                        logger.info(f"获取港股 {stock_code} 的历史数据")
                        try:
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