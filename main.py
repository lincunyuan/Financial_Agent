import os
import sys
import logging
import uuid
import yaml

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入核心模块
from core.mcp import (
    get_plugin_manager,
    add_plugin_directory,
    enable_hot_reload,
    shutdown_plugin_manager
)
from core.intent_recognizer import IntentRecognizer
from core.prompt_engine import PromptEngine
from core.llm_client import LLMClient
from core.langchain_tools import get_all_langchain_tools
from core.langchain_rag import FinancialRAG
from core.langchain_graph import FinancialAgentGraph
from core.session_manager import RedisSessionManager
from core.chart_generator import ChartGenerator
from utils.config_loader import default_config_loader

# 加载配置
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'model_config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    """主函数"""
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='金融助手服务')
    parser.add_argument('--mode', choices=['cli', 'web'], default='cli', help='运行模式: cli(命令行) 或 web(网页界面)')
    args = parser.parse_args()
    
    # 如果选择web模式，启动Streamlit前端
    if args.mode == 'web':
        import subprocess
        import sys
        
        print("=== 启动金融助手前端界面 ===")
        print("正在启动Streamlit服务器...")
        
        # 启动Streamlit
        streamlit_command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            "8501",
            "--server.address",
            "localhost"
        ]
        
        subprocess.run(streamlit_command)
    try:
        logger.info("=== 金融助手服务启动 (LangChain增强版) ===")
        
        # 加载配置
        config = load_config()
        logger.info(f"加载的配置内容: {config}")
        config_loader = default_config_loader
        
        # 初始化插件管理器
        logger.info("初始化插件管理器...")
        plugin_manager = get_plugin_manager()
        
        # 添加插件目录
        plugin_dir = os.path.join(os.path.dirname(__file__), 'core', 'plugins')
        if os.path.exists(plugin_dir):
            add_plugin_directory(plugin_dir)
            logger.info(f"已添加插件目录: {plugin_dir}")
        
        # 启用热更新
        enable_hot_reload(interval=5)
        logger.info("插件热更新已启用")
        
        # 初始化LLM客户端
        llm_client = LLMClient(config_path=os.path.join("config", "model_config.yaml"))
        
        # 初始化意图识别器
        intent_recognizer = IntentRecognizer()
        logger.info("意图识别器初始化完成")
        
        # 初始化LangChain工具
        tools = get_all_langchain_tools()
        logger.info(f"加载了 {len(tools)} 个LangChain工具")
        
        # 初始化RAG模块
        rag = None
        try:
            # 从配置中获取base_url
            base_url = config.get("base_url")
            api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
            
            rag = FinancialRAG(
                llm=llm_client.client,
                api_key=api_key,
                base_url=base_url
            )
            logger.info("RAG模块初始化完成")
        except Exception as e:
            logger.warning(f"RAG模块初始化失败: {e}")
        
        # 初始化提示词引擎（集成RAG）
        prompt_engine = PromptEngine(config={}, rag=rag)
        logger.info("提示词引擎初始化完成")
        
        # 初始化Redis会话存储
        session_manager = None
        try:
            session_manager = RedisSessionManager()
            logger.info("Redis会话存储初始化完成")
        except Exception as e:
            logger.warning(f"Redis会话存储初始化失败: {e}")
        
        # 初始化图表生成器
        chart_generator = ChartGenerator()
        logger.info("图表生成器初始化完成")
        
        # 初始化LangGraph工作流
        agent_graph = FinancialAgentGraph(
            intent_recognizer=intent_recognizer,
            tools=tools,
            nlg_engine=prompt_engine,
            llm_client=llm_client,
            chart_generator=chart_generator,
            rag=rag,
            session_storage=session_manager
        )
        logger.info("LangGraph工作流初始化完成")
        
        # 启动命令行交互
        logger.info("金融助手服务已启动，等待用户输入...")
        print("\n=== 财经助手 (LangChain增强版) ===")
        print("输入 'exit' 或 'quit' 退出程序")
        print("\n")
        
        # 生成唯一用户ID
        user_id = str(uuid.uuid4())
        logger.info(f"生成用户ID: {user_id}")
        
        try:
            while True:
                # 获取用户输入
                query = input("用户: ").strip()
                
                # 检查是否退出
                if query.lower() in ['exit', 'quit']:
                    logger.info("程序退出")
                    break
                
                if not query:
                    continue
                
                # 处理查询
                logger.info("处理查询中...")
                try:
                    # 运行工作流
                    mcp_result = agent_graph.run(query, user_id=user_id)
                    
                    # 显示结果
                    print(f"\n助手: {mcp_result.get('response', '抱歉，我无法回答这个问题。')}")
                    
                    # 如果有工具调用结果，显示
                    if mcp_result.get('context', {}).get('realtime_data'):
                        print(f"\n工具调用结果: {mcp_result['context']['realtime_data']}")
                    
                    # 如果有RAG检索结果，显示来源
                    if mcp_result.get('context', {}).get('knowledge_base_content'):
                        print(f"\n知识库来源: {len(mcp_result['context']['knowledge_base_content'])} 个相关片段")
                    
                    print("\n" + "="*50 + "\n")
                    logger.info("查询处理完成")
                except Exception as e:
                    logger.error(f"处理查询时出错: {e}")
                    print(f"\n助手: 抱歉，处理您的请求时出错了。\n")
                    
        except KeyboardInterrupt:
            logger.info("程序被中断，退出")
        except Exception as e:
            logger.error(f"交互过程中发生错误: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}", exc_info=True)
        print(f"初始化失败: {e}")
        sys.exit(1)
    finally:
        # 关闭插件管理器
        shutdown_plugin_manager()

if __name__ == "__main__":
    main()