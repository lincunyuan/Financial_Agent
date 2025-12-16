import streamlit as st
import sys
import os
import yaml
import uuid
from core.langchain_graph import FinancialAgentGraph
from utils.config_loader import default_config_loader
from core.mcp.plugin_manager import PluginManager
from core.llm_client import LLMClient
from core.intent_recognizer import IntentRecognizer
from core.langchain_tools import get_all_langchain_tools
from core.langchain_rag import FinancialRAG as RAG
from core.prompt_engine import PromptEngine
from core.session_manager import RedisSessionManager
from core.chart_generator import ChartGenerator

# 设置页面标题和布局
st.set_page_config(
    page_title="金融助手",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面标题
st.title("金融助手智能查询系统")

# 侧边栏
st.sidebar.title("功能说明")
st.sidebar.write("这是一个金融助手智能查询系统，可以帮助您查询股票价格、财务指标等信息。")
st.sidebar.write("\n**使用示例：**")
st.sidebar.write("- 贵州茅台的股价是多少？")
st.sidebar.write("- 工商银行的市值是多少？")
st.sidebar.write("- 中国平安的市盈率是多少？")

# 初始化应用
@st.cache_resource
def init_app():
    # 加载配置
    model_config = default_config_loader.load_config("model_config.yaml")
    api_keys = default_config_loader.load_config("api_keys.yaml")
    
    # 初始化插件管理器
    plugin_manager = PluginManager()
    
    # 初始化LLM客户端
    llm_client = LLMClient()
    
    # 初始化意图识别器
    intent_recognizer = IntentRecognizer()
    
    # 加载LangChain工具
    langchain_tools = get_all_langchain_tools()
    
    # 初始化RAG模块
    rag = None  # 暂时不初始化RAG，避免导入错误
    
    # 初始化提示词引擎
    prompt_engine = PromptEngine(model_config)
    
    # 初始化Redis会话存储
    session_storage = RedisSessionManager()
    
    # 初始化图表生成器
    chart_generator = ChartGenerator()
    
    # 初始化LangGraph工作流
    agent_graph = FinancialAgentGraph(
        intent_recognizer=intent_recognizer,
        tools=langchain_tools,
        nlg_engine=prompt_engine,
        llm_client=llm_client,
        chart_generator=chart_generator,
        rag=rag,
        session_storage=session_storage
    )
    
    return agent_graph

# 初始化应用
agent_graph = init_app()

# 会话历史和会话ID
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 为每个新会话生成唯一ID
    st.session_state.session_id = str(uuid.uuid4())

# 显示会话历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("请输入您的金融问题..."):
    # 添加用户消息到会话历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 处理用户查询
    with st.chat_message("assistant"):
        # 创建流式响应
        response_placeholder = st.empty()
        
        # 处理用户请求
        try:
            # 调用agent_graph处理查询
            # 注意：需要根据实际的agent_graph接口进行调整
            result = agent_graph.run(prompt, user_id=st.session_state.session_id)
            
            # 从结果中提取响应内容
            response = result.get('response', '抱歉，我无法回答这个问题。')
            
            # 显示响应
            response_placeholder.markdown(response)
            
            # 显示图表（如果有）
            if "kline_chart" in result and result["kline_chart"]:
                st.markdown("### K线图")
                st.plotly_chart(result["kline_chart"], use_container_width=True)
            if "line_chart" in result and result["line_chart"]:
                st.markdown("### 价格走势图")
                st.plotly_chart(result["line_chart"], use_container_width=True)
            if "volume_chart" in result and result["volume_chart"]:
                st.markdown("### 成交量图")
                st.plotly_chart(result["volume_chart"], use_container_width=True)
            
            # 添加助手响应到会话历史
            # 由于图表是交互式对象，只保存图表类型信息到会话历史
            message_content = response
            if "kline_chart" in result and result["kline_chart"]:
                message_content += "\n\n[已生成K线图]\n"
            if "line_chart" in result and result["line_chart"]:
                message_content += "[已生成价格走势图]\n"
            if "volume_chart" in result and result["volume_chart"]:
                message_content += "[已生成成交量图]\n"
            
            st.session_state.messages.append({"role": "assistant", "content": message_content})
            
            # 显示思考过程（如果有）
            thinking_process = result.get('thinking_process', [])
            if thinking_process:
                with st.expander("思考过程"):
                    for step in thinking_process:
                        with st.container():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"**{step['step']}**")
                                st.caption(step['timestamp'].split('T')[1].split('.')[0])
                            with col2:
                                st.markdown(f"**{step['description']}**")
                                st.markdown(f"{step['details']}")
                            st.divider()
        except Exception as e:
            # 显示错误信息
            error_msg = f"处理请求时发生错误：{str(e)}"
            response_placeholder.markdown(error_msg)
            
            # 添加错误信息到会话历史
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

# 页脚信息
st.markdown("---")
st.markdown("© 2024 金融助手智能查询系统")