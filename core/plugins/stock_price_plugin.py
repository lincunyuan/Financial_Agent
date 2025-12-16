# 股票价格查询插件

import akshare as ak
import logging
from typing import Dict, Any
from datetime import datetime

from core.mcp import BasePlugin, register_plugin

logger = logging.getLogger(__name__)


class StockPricePlugin(BasePlugin):
    """股票价格查询插件"""
    plugin_name = "stock_price_plugin"
    plugin_version = "1.0.0"
    plugin_description = "查询股票实时价格数据"
    plugin_author = "Financial Assistant Agent"
    
    def __init__(self):
        super().__init__()
        self._data_source = None
    
    def initialize(self) -> bool:
        """初始化插件"""
        try:
            # 导入数据集成模块
            from core.tool_integration import FinancialDataAPI
            self._data_source = FinancialDataAPI()
            logger.info(f"{self.plugin_name} 初始化成功")
            return True
        except Exception as e:
            logger.error(f"{self.plugin_name} 初始化失败: {e}")
            return False
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行插件逻辑"""
        try:
            # 获取参数
            stock_code = kwargs.get('code')
            time = kwargs.get('time')
            
            if not stock_code:
                return {
                    'success': False,
                    'error': '缺少股票代码参数',
                    'data': None
                }
            
            # 调用数据源获取股票价格
            result = self._data_source.get_stock_price(stock_code, time)
            
            return {
                'success': True,
                'error': None,
                'data': result
            }
        except Exception as e:
            logger.error(f"{self.plugin_name} 执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }


# 注册插件
register_plugin(StockPricePlugin.plugin_name, StockPricePlugin)