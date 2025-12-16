# MCP核心接口规范 - 插件管理器
# 实现插件的"注册-发现-调用"机制，支持热更新

import os
import sys
import importlib
import threading
import time
import logging
from typing import Dict, Any, Callable, Type, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginMeta(type):
    """插件元类，用于自动注册插件"""
    _plugins = {}
    
    def __new__(cls, name: str, bases: tuple, attrs: dict):
        new_class = super().__new__(cls, name, bases, attrs)
        
        # 跳过抽象基类
        if not attrs.get('__abstract__', False) and name != 'BasePlugin':
            plugin_name = attrs.get('plugin_name', name.lower())
            PluginMeta._plugins[plugin_name] = new_class
            logger.info(f"插件自动注册: {plugin_name}")
        
        return new_class


class BasePlugin(metaclass=PluginMeta):
    """插件基类，所有MCP插件必须继承此类"""
    __abstract__ = True
    plugin_name: str = ""
    plugin_version: str = "1.0.0"
    plugin_description: str = ""
    plugin_author: str = ""
    
    def __init__(self):
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """初始化插件"""
        self._is_initialized = True
        logger.info(f"插件初始化: {self.plugin_name} v{self.plugin_version}")
        return True
    
    def shutdown(self) -> bool:
        """关闭插件"""
        self._is_initialized = False
        logger.info(f"插件关闭: {self.plugin_name}")
        return True
    
    def is_initialized(self) -> bool:
        """检查插件是否已初始化"""
        return self._is_initialized
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行插件逻辑，必须由子类实现"""
        raise NotImplementedError("插件必须实现execute方法")
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取插件元数据"""
        return {
            'name': self.plugin_name,
            'version': self.plugin_version,
            'description': self.plugin_description,
            'author': self.plugin_author,
            'initialized': self._is_initialized
        }


class PluginManager:
    """MCP插件管理器，实现插件的注册、发现、调用和热更新"""
    
    def __init__(self, plugin_dirs: Optional[list] = None):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        self._plugin_dirs: list = plugin_dirs or []
        self._hot_reload_enabled: bool = False
        self._hot_reload_thread: Optional[threading.Thread] = None
        self._hot_reload_interval: int = 5  # 热更新检查间隔（秒）
        self._plugin_file_mtimes: Dict[str, float] = {}  # 插件文件的修改时间
        
        # 加载初始插件
        self._load_initial_plugins()
    
    def _load_initial_plugins(self):
        """加载初始插件"""
        # 从元类中获取自动注册的插件
        for plugin_name, plugin_class in PluginMeta._plugins.items():
            self.register_plugin(plugin_name, plugin_class)
    
    def register_plugin(self, plugin_name: str, plugin_class: Type[BasePlugin]) -> bool:
        """注册插件"""
        try:
            if plugin_name in self._plugins:
                logger.warning(f"插件已存在: {plugin_name}")
                return False
            
            # 创建插件实例并初始化
            plugin_instance = plugin_class()
            plugin_instance.plugin_name = plugin_name
            if plugin_instance.initialize():
                self._plugins[plugin_name] = plugin_instance
                self._plugin_classes[plugin_name] = plugin_class
                logger.info(f"插件注册成功: {plugin_name}")
                return True
            else:
                logger.error(f"插件初始化失败: {plugin_name}")
                return False
        except Exception as e:
            logger.error(f"插件注册错误: {plugin_name} - {str(e)}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """注销插件"""
        try:
            if plugin_name not in self._plugins:
                logger.warning(f"插件不存在: {plugin_name}")
                return False
            
            # 关闭插件
            plugin = self._plugins[plugin_name]
            plugin.shutdown()
            
            # 移除插件
            del self._plugins[plugin_name]
            if plugin_name in self._plugin_classes:
                del self._plugin_classes[plugin_name]
            
            logger.info(f"插件注销成功: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"插件注销错误: {plugin_name} - {str(e)}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_name)
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的插件"""
        plugins_info = {}
        for plugin_name, plugin in self._plugins.items():
            plugins_info[plugin_name] = plugin.get_metadata()
        return plugins_info
    
    def call(self, plugin_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用插件"""
        try:
            plugin = self.get_plugin(plugin_name)
            if not plugin:
                return {
                    'success': False,
                    'error': f"插件不存在: {plugin_name}",
                    'data': None
                }
            
            if not plugin.is_initialized():
                return {
                    'success': False,
                    'error': f"插件未初始化: {plugin_name}",
                    'data': None
                }
            
            # 执行插件
            result = plugin.execute(**(params or {}))
            return {
                'success': True,
                'error': None,
                'data': result
            }
        except Exception as e:
            logger.error(f"插件调用错误: {plugin_name} - {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def add_plugin_directory(self, dir_path: str) -> bool:
        """添加插件目录"""
        try:
            dir_path = os.path.abspath(dir_path)
            if not os.path.exists(dir_path):
                logger.error(f"插件目录不存在: {dir_path}")
                return False
            
            if dir_path not in self._plugin_dirs:
                self._plugin_dirs.append(dir_path)
                # 将目录添加到Python路径
                if dir_path not in sys.path:
                    sys.path.append(dir_path)
                logger.info(f"添加插件目录成功: {dir_path}")
            
            # 立即扫描并加载新目录中的插件
            self._scan_plugin_directory(dir_path)
            return True
        except Exception as e:
            logger.error(f"添加插件目录错误: {dir_path} - {str(e)}")
            return False
    
    def _scan_plugin_directory(self, dir_path: str):
        """扫描插件目录并加载插件"""
        try:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        plugin_file = os.path.join(root, file)
                        self._load_plugin_file(plugin_file)
        except Exception as e:
            logger.error(f"扫描插件目录错误: {dir_path} - {str(e)}")
    
    def _load_plugin_file(self, file_path: str):
        """加载单个插件文件"""
        try:
            # 获取模块名
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 检查文件是否已修改
            current_mtime = os.path.getmtime(file_path)
            if file_path in self._plugin_file_mtimes and current_mtime == self._plugin_file_mtimes[file_path]:
                return  # 文件未修改，无需重新加载
            
            # 导入或重新加载模块
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                logger.info(f"重新加载插件: {module_name}")
            else:
                importlib.import_module(module_name)
                logger.info(f"加载插件: {module_name}")
            
            # 更新修改时间
            self._plugin_file_mtimes[file_path] = current_mtime
        except Exception as e:
            logger.error(f"加载插件文件错误: {file_path} - {str(e)}")
    
    def enable_hot_reload(self, interval: int = 5):
        """启用热更新"""
        if self._hot_reload_enabled:
            logger.info("热更新已启用")
            return
        
        self._hot_reload_enabled = True
        self._hot_reload_interval = interval
        
        # 创建热更新线程
        self._hot_reload_thread = threading.Thread(target=self._hot_reload_loop, daemon=True)
        self._hot_reload_thread.start()
        logger.info(f"热更新已启用，检查间隔: {interval}秒")
    
    def disable_hot_reload(self):
        """禁用热更新"""
        self._hot_reload_enabled = False
        if self._hot_reload_thread:
            self._hot_reload_thread.join(timeout=1)
        logger.info("热更新已禁用")
    
    def _hot_reload_loop(self):
        """热更新检查循环"""
        while self._hot_reload_enabled:
            try:
                # 扫描所有插件目录
                for plugin_dir in self._plugin_dirs:
                    self._scan_plugin_directory(plugin_dir)
                
                # 等待指定间隔
                time.sleep(self._hot_reload_interval)
            except Exception as e:
                logger.error(f"热更新循环错误: {str(e)}")
                time.sleep(self._hot_reload_interval)
    
    def shutdown(self):
        """关闭插件管理器"""
        # 禁用热更新
        self.disable_hot_reload()
        
        # 注销所有插件
        plugin_names = list(self._plugins.keys())
        for plugin_name in plugin_names:
            self.unregister_plugin(plugin_name)
        
        logger.info("插件管理器已关闭")


# 全局插件管理器实例
_plugin_manager_instance: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance


# 便捷函数
def register_plugin(plugin_name: str, plugin_class: Type[BasePlugin]) -> bool:
    """便捷注册插件"""
    return get_plugin_manager().register_plugin(plugin_name, plugin_class)


def unregister_plugin(plugin_name: str) -> bool:
    """便捷注销插件"""
    return get_plugin_manager().unregister_plugin(plugin_name)


def call_plugin(plugin_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """便捷调用插件"""
    return get_plugin_manager().call(plugin_name, params)


def list_plugins() -> Dict[str, Dict[str, Any]]:
    """便捷列出插件"""
    return get_plugin_manager().list_plugins()


def add_plugin_directory(dir_path: str) -> bool:
    """便捷添加插件目录"""
    return get_plugin_manager().add_plugin_directory(dir_path)


def enable_hot_reload(interval: int = 5):
    """便捷启用热更新"""
    get_plugin_manager().enable_hot_reload(interval)


def disable_hot_reload():
    """便捷禁用热更新"""
    get_plugin_manager().disable_hot_reload()


def shutdown_plugin_manager():
    """便捷关闭插件管理器"""
    get_plugin_manager().shutdown()