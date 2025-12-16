# MCP核心接口规范 - 数据源插件接口
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod
from datetime import datetime


class DataSourcePlugin(ABC):
    """数据源插件基类，所有数据源插件必须实现此接口"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """获取数据源版本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass


class MarketDataAPI(DataSourcePlugin):
    """行情数据API接口规范"""
    
    @abstractmethod
    def get_stock_price(self, stock_code: str, time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取股票实时/历史价格数据
        
        Args:
            stock_code: 股票代码，格式如 "600519.SS"（A股）、"AAPL.US"（美股）、"0700.HK"（港股）
            time: 可选，指定时间点的历史数据
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'price': float,  # 当前/指定时间价格
                'change': float,  # 涨跌幅（百分比）
                'change_amount': float,  # 涨跌额
                'volume': int,  # 成交量
                'amount': float,  # 成交额
                'high': float,  # 最高价
                'low': float,  # 最低价
                'open': float,  # 开盘价
                'prev_close': float,  # 昨日收盘价
                'timestamp': str,  # 数据时间戳
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def get_market_index(self, index_name: str, time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取市场指数数据
        
        Args:
            index_name: 指数名称，如 "上证指数"、"深证成指"、"纳斯达克指数"
            time: 可选，指定时间点的历史数据
            
        Returns:
            Dict: {
                'name': str,  # 指数名称
                'price': float,  # 当前/指定时间点位
                'change': float,  # 涨跌幅（百分比）
                'change_amount': float,  # 涨跌点
                'volume': int,  # 成交量
                'amount': float,  # 成交额
                'timestamp': str,  # 数据时间戳
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def get_intraday_data(self, symbol: str, interval: str = "5min", limit: int = 100) -> Dict[str, Any]:
        """获取日内交易数据
        
        Args:
            symbol: 股票/指数代码
            interval: 时间间隔，如 "1min", "5min", "15min", "30min", "1h"
            limit: 返回数据点数量
            
        Returns:
            Dict: {
                'symbol': str,  # 代码
                'interval': str,  # 时间间隔
                'data': List[Dict],  # 数据点列表
                'source': str  # 数据源
            }
        """
        pass


class StockDataAPI(DataSourcePlugin):
    """股票数据API接口规范（如Alpha Vantage）"""
    
    @abstractmethod
    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'name': str,  # 股票名称
                'industry': str,  # 所属行业
                'market': str,  # 所属市场
                'currency': str,  # 交易货币
                'exchange': str,  # 交易所
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def get_historical_data(self, stock_code: str, start_date: datetime, end_date: datetime, 
                           interval: str = "1d") -> Dict[str, Any]:
        """获取历史K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间间隔，如 "1d", "1w", "1mo"
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'interval': str,  # 时间间隔
                'data': List[Dict],  # K线数据列表，每条包含 open, high, low, close, volume, timestamp
                'source': str  # 数据源
            }
        """
        pass


class NewsAPI(DataSourcePlugin):
    """新闻舆情API接口规范（如NewsAPI）"""
    
    @abstractmethod
    def get_financial_news(self, query: str = "", category: str = "finance", 
                          limit: int = 10, language: str = "zh") -> Dict[str, Any]:
        """获取财经新闻
        
        Args:
            query: 搜索关键词
            category: 新闻类别
            limit: 返回新闻数量
            language: 新闻语言
            
        Returns:
            Dict: {
                'articles': List[Dict],  # 新闻列表
                'total': int,  # 总数量
                'timestamp': str,  # 请求时间戳
                'sources': List[str]  # 数据源列表
            }
        """
        pass
    
    @abstractmethod
    def get_news_by_topic(self, topic: str, limit: int = 10) -> Dict[str, Any]:
        """按主题获取新闻
        
        Args:
            topic: 主题关键词
            limit: 返回新闻数量
            
        Returns:
            Dict: 同 get_financial_news
        """
        pass


class EconomicDataAPI(DataSourcePlugin):
    """经济数据API接口规范"""
    
    @abstractmethod
    def get_economic_indicator(self, indicator: str, start_date: Optional[datetime] = None, 
                              end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取经济指标数据
        
        Args:
            indicator: 指标名称，如 "GDP", "CPI", "PPI", "PMI"
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: {
                'indicator': str,  # 指标名称
                'data': List[Dict],  # 指标数据列表
                'source': str,  # 数据源
                'timestamp': str  # 请求时间戳
            }
        """
        pass