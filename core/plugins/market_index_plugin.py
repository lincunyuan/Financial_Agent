# 市场指数查询插件

import akshare as ak
import logging
from typing import Dict, Any
from datetime import datetime

from core.mcp import BasePlugin, register_plugin

logger = logging.getLogger(__name__)


class MarketIndexPlugin(BasePlugin):
    """市场指数查询插件"""
    plugin_name = "market_index_plugin"
    plugin_version = "1.0.0"
    plugin_description = "查询市场指数数据"
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
            index_name = kwargs.get('name', '上证指数')
            time = kwargs.get('time')
            
            # 调用数据源获取指数数据
            result = self._data_source.get_market_index(index_name, time)
            
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
register_plugin(MarketIndexPlugin.plugin_name, MarketIndexPlugin)