# MCP核心接口规范包
from .data_source_api import (
    DataSourcePlugin,
    MarketDataAPI,
    StockDataAPI,
    NewsAPI,
    EconomicDataAPI
)

from .tool_plugin_api import (
    ToolPlugin,
    TechnicalIndicatorTool,
    RiskAnalysisTool,
    FinancialCalculationTool
)

from .context_storage_api import (
    ContextStorage,
    SessionStorage,
    CacheStorage,
    RedisSessionStorage
)

# 插件管理器
from .plugin_manager import (
    PluginManager,
    BasePlugin,
    PluginMeta,
    get_plugin_manager,
    register_plugin,
    unregister_plugin,
    call_plugin,
    list_plugins,
    add_plugin_directory,
    enable_hot_reload,
    disable_hot_reload,
    shutdown_plugin_manager
)

__all__ = [
    # 数据源接口
    'DataSourcePlugin',
    'MarketDataAPI',
    'StockDataAPI',
    'NewsAPI',
    'EconomicDataAPI',
    
    # 工具接口
    'ToolPlugin',
    'TechnicalIndicatorTool',
    'RiskAnalysisTool',
    'FinancialCalculationTool',
    
    # 上下文存储接口
    'ContextStorage',
    'SessionStorage',
    'CacheStorage',
    'RedisSessionStorage',
    
    # 插件管理器
    'PluginManager',
    'BasePlugin',
    'PluginMeta',
    'get_plugin_manager',
    'register_plugin',
    'unregister_plugin',
    'call_plugin',
    'list_plugins',
    'add_plugin_directory',
    'enable_hot_reload',
    'disable_hot_reload',
    'shutdown_plugin_manager'
]