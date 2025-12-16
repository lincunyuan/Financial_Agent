# MCP核心接口规范 - 工具插件接口
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod
from datetime import datetime


class ToolPlugin(ABC):
    """工具插件基类，所有工具插件必须实现此接口"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """获取工具版本"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查工具是否可用"""
        pass


class TechnicalIndicatorTool(ToolPlugin):
    """技术指标工具接口规范"""
    
    @abstractmethod
    def get_technical_indicators(self, stock_code: str, indicators: List[str], 
                                period: int = 14, interval: str = "1d") -> Dict[str, Any]:
        """获取股票技术指标
        
        Args:
            stock_code: 股票代码
            indicators: 指标列表，如 ["MACD", "RSI", "MA", "KDJ", "BOLL"]
            period: 计算周期，默认14天
            interval: 时间间隔，如 "1d", "1w", "1mo"
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'timestamp': str,  # 计算时间戳
                'indicators': Dict[str, Any],  # 指标结果字典
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def calculate_macd(self, stock_code: str, fast_period: int = 12, 
                      slow_period: int = 26, signal_period: int = 9) -> Dict[str, Any]:
        """计算MACD指标
        
        Args:
            stock_code: 股票代码
            fast_period: 快速移动平均线周期
            slow_period: 慢速移动平均线周期
            signal_period: 信号线周期
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'macd': float,  # MACD值
                'signal': float,  # 信号线值
                'histogram': float,  # MACD柱状图
                'timestamp': str,  # 计算时间戳
                'signal': str  # 买卖信号 (buy/sell/hold)
            }
        """
        pass
    
    @abstractmethod
    def calculate_rsi(self, stock_code: str, period: int = 14) -> Dict[str, Any]:
        """计算RSI指标
        
        Args:
            stock_code: 股票代码
            period: 计算周期
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'rsi': float,  # RSI值
                'timestamp': str,  # 计算时间戳
                'signal': str  # 买卖信号 (buy/sell/hold)
            }
        """
        pass
    
    @abstractmethod
    def calculate_ma(self, stock_code: str, periods: List[int] = [5, 10, 20, 60]) -> Dict[str, Any]:
        """计算移动平均线
        
        Args:
            stock_code: 股票代码
            periods: 周期列表
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'ma': Dict[int, float],  # 各周期MA值
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass


class RiskAnalysisTool(ToolPlugin):
    """风险分析工具接口规范"""
    
    @abstractmethod
    def calculate_risk(self, stock_code: str, period: int = 252) -> Dict[str, Any]:
        """计算股票风险指标
        
        Args:
            stock_code: 股票代码
            period: 计算周期（默认252个交易日）
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'volatility': float,  # 波动率
                'beta': float,  # β系数
                'sharpe_ratio': float,  # 夏普比率
                'sortino_ratio': float,  # 索提诺比率
                'max_drawdown': float,  # 最大回撤
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def calculate_var(self, stock_code: str, confidence_level: float = 0.95, 
                     period: int = 252) -> Dict[str, Any]:
        """计算VaR（Value at Risk）
        
        Args:
            stock_code: 股票代码
            confidence_level: 置信水平
            period: 计算周期
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'var': float,  # VaR值
                'confidence_level': float,  # 置信水平
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def analyze_portfolio_risk(self, portfolio: Dict[str, float], 
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """分析投资组合风险
        
        Args:
            portfolio: 投资组合，格式为 {"stock_code": weight, ...}
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: {
                'portfolio': Dict[str, float],  # 投资组合
                'total_value': float,  # 组合总价值
                'volatility': float,  # 组合波动率
                'beta': float,  # 组合β系数
                'sharpe_ratio': float,  # 组合夏普比率
                'max_drawdown': float,  # 组合最大回撤
                'return': float,  # 组合收益率
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass


class FinancialCalculationTool(ToolPlugin):
    """财务计算工具接口规范"""
    
    @abstractmethod
    def calculate_dcf(self, stock_code: str, discount_rate: float = 0.1, 
                     growth_rate: float = 0.05) -> Dict[str, Any]:
        """计算DCF（贴现现金流）估值
        
        Args:
            stock_code: 股票代码
            discount_rate: 贴现率
            growth_rate: 增长率
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'intrinsic_value': float,  # 内在价值
                'fair_price': float,  # 合理价格
                'current_price': float,  # 当前价格
                'discount_rate': float,  # 贴现率
                'growth_rate': float,  # 增长率
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass
    
    @abstractmethod
    def calculate_financial_ratios(self, stock_code: str) -> Dict[str, Any]:
        """计算财务比率
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: {
                'symbol': str,  # 股票代码
                'profitability': Dict[str, float],  # 盈利能力比率
                'liquidity': Dict[str, float],  # 流动性比率
                'solvency': Dict[str, float],  # 偿债能力比率
                'valuation': Dict[str, float],  # 估值比率
                'timestamp': str,  # 计算时间戳
                'source': str  # 数据源
            }
        """
        pass