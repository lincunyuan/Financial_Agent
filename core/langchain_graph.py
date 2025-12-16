# LangGraph工作流模块 - 协调NLU、工具调用和NLG
from langgraph.graph import StateGraph, END
from langchain_core.runnables.base import RunnableConfig
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import pandas as pd

# 导入MCP核心接口
from core.mcp import SessionStorage

# 设置日志
logger = logging.getLogger(__name__)

# 定义工作流状态
class FinancialAgentState(Dict):
    """金融助手工作流状态"""
    user_input: str
    intent: Optional[str]
    entities: Optional[Dict]
    tool_result: Optional[Dict]
    response: Optional[str]
    context: Optional[Dict]
    error: Optional[str]
    user_id: str
    thinking_process: Optional[List[Dict]]  # 记录思考过程

class FinancialAgentGraph:
    """金融助手工作流图"""
    
    def __init__(self, intent_recognizer, tools, nlg_engine, llm_client, chart_generator=None, rag=None, session_storage: Optional[SessionStorage] = None):
        """初始化工作流图
        
        Args:
            intent_recognizer: 意图识别器
            tools: LangChain工具列表
            nlg_engine: 自然语言生成引擎
            llm_client: LLM客户端，用于实际生成回答
            rag: RAG模块（可选）
            session_storage: MCP会话存储接口实现（可选）
        """
        self.intent_recognizer = intent_recognizer
        self.tools = tools
        self.nlg_engine = nlg_engine
        self.llm_client = llm_client
        self.rag = rag
        self.session_storage = session_storage
        self.chart_generator = chart_generator
        self.graph = None
        
        # 保存工具列表
        self.tools = tools
        
        # 创建工具映射，方便根据意图调用
        self.tool_map = {
                "query_stock_price": self._call_get_stock_price,
                "specific_stock": self._call_get_stock_price,
                "query_market_index": self._call_get_market_index,
                "query_financial_news": self._call_get_financial_news,
                "query_economic_data": self._call_get_economic_data,
                "stock_historical_data": self._call_get_stock_historical_data
            }
        
        # 初始化工作流图
        self._build_graph()
    
    def _build_graph(self):
        """构建工作流图"""
        # 创建状态图
        self.graph = StateGraph(FinancialAgentState)
        
        # 添加节点
        self.graph.add_node("nlu", self._nlu_node)
        self.graph.add_node("tool_call", self._tool_call_node)
        self.graph.add_node("nlg", self._nlg_node)
        
        # 添加条件边
        self.graph.add_conditional_edges(
            "nlu",
            self._should_call_tool,
            {
                True: "tool_call",
                False: "nlg"
            }
        )
        
        # 添加工具调用后的边
        self.graph.add_edge("tool_call", "nlg")
        
        # 设置入口点
        self.graph.set_entry_point("nlu")
        
        # 编译图
        self.graph = self.graph.compile()
    
    def _nlu_node(self, state: FinancialAgentState) -> Dict[str, Any]:
        """NLU节点 - 处理用户输入，识别意图和实体
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        try:
            # 初始化思考过程
            thinking_process = state.get('thinking_process', [])
            thinking_process.append({
                "step": "nlu",
                "description": "开始意图识别和实体提取",
                "details": f"用户输入: {state['user_input']}",
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"NLU节点处理用户输入: {state['user_input']}")
            logger.info(f"会话存储对象: {self.session_storage}")
            logger.info(f"会话存储方法: {hasattr(self.session_storage, 'get_conversation_history')}")
            
            # 获取历史对话上下文
            history = []
            if self.session_storage and hasattr(self.session_storage, 'get_conversation_history'):
                try:
                    user_id = state.get('user_id', 'default_user')
                    logger.info(f"获取历史对话，用户ID: {user_id}")
                    raw_history = self.session_storage.get_conversation_history(user_id, limit=5)  # 获取最近5轮对话
                    logger.info(f"原始历史对话: {raw_history}")
                    history = [(item['query'], item['response']) for item in raw_history]
                    logger.info(f"转换后的历史对话: {history}")
                    
                    thinking_process.append({
                        "step": "nlu",
                        "description": "获取历史对话上下文",
                        "details": f"已获取最近{len(history)}轮对话",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"获取历史对话失败: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    thinking_process.append({
                        "step": "nlu",
                        "description": "获取历史对话上下文",
                        "details": f"失败: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            # 获取指代关系
            coreferences = []
            if self.session_storage and hasattr(self.session_storage, 'get_coreferences'):
                try:
                    user_id = state.get('user_id', 'default_user')
                    coreferences = self.session_storage.get_coreferences(user_id)
                    logger.info(f"获取指代关系，用户ID: {user_id}，结果: {coreferences}")
                except Exception as e:
                    logger.warning(f"获取指代关系失败: {e}")
            
            # 调用意图识别器，传入历史对话上下文和指代关系
            thinking_process.append({
                "step": "nlu",
                "description": "调用意图识别器",
                "details": "分析用户输入、历史对话和指代关系",
                "timestamp": datetime.now().isoformat()
            })
            
            result = self.intent_recognizer.analyze(state['user_input'], history, coreferences)
            
            # 提取意图和实体 - 兼容'primary_intent'和'intent'字段
            intent = result.get("primary_intent", result.get("intent", "unknown"))
            entities = result.get("entities", {})
            
            logger.info(f"识别到意图: {intent}, 实体: {entities}")
            
            thinking_process.append({
                "step": "nlu",
                "description": "意图识别完成",
                "details": f"识别到意图: {intent}, 实体: {entities}",
                "timestamp": datetime.now().isoformat()
            })
            
            # 存储指代关系
            if self.session_storage and hasattr(self.session_storage, 'store_coreference'):
                try:
                    user_id = state.get('user_id', 'default_user')
                    
                    # 如果有解析出的代词，存储解析结果
                    resolved_pronouns = result.get('resolved_pronouns', [])
                    if resolved_pronouns:
                        for resolved in resolved_pronouns:
                            logger.info(f"存储代词指代关系：user_id={user_id}, pronoun={resolved.get('pronoun')}, type={resolved.get('type')}, target={resolved.get('target')}, value={resolved.get('value')}")
                            self.session_storage.store_coreference(
                                user_id,
                                pronoun=resolved.get('pronoun'),
                                referent_type=resolved.get('type', 'entity'),
                                referent_target=resolved.get('target', 'stock'),
                                referent_value=resolved.get('value')
                            )
                    # 如果没有解析出的代词，但识别到了实体，为可能的后续代词（如"它"）存储指代关系
                    elif entities:
                        logger.info(f"没有解析出代词，但识别到实体：{entities}")
                        for entity in entities:
                            entity_type = entity.get('type')
                            # 检查实体类型是否与我们支持的类型匹配
                            if entity_type in ['stock', 'index', 'company', 'stock_name', 'stock_code', 'index_name', 'index_code']:
                                logger.info(f"实体类型匹配：{entity_type}")
                                # 统一实体类型为内部使用的类型
                                internal_type = 'stock' if entity_type in ['stock_name', 'stock_code'] else 'index' if entity_type in ['index_name', 'index_code'] else entity_type
                                logger.info(f"存储代词'它'的指代关系：user_id={user_id}, type={internal_type}, target={entity_type}, value={entity.get('value') or entity.get('name')}")
                                self.session_storage.store_coreference(
                                    user_id,
                                    pronoun='它',  # 为最常用的代词创建指代关系
                                    referent_type=internal_type,
                                    referent_target=entity_type,
                                    referent_value=entity.get('value') or entity.get('name')
                                )
                except Exception as e:
                    logger.warning(f"存储指代关系失败: {e}")
            
            return {
                "intent": intent,
                "entities": entities,
                "resolved_pronouns": result.get("resolved_pronouns", []),
                "context": result.get("context", {}),
                "thinking_process": thinking_process,
                "user_id": state.get('user_id', 'default_user')
            }
            
        except Exception as e:
            logger.error(f"NLU节点处理失败: {e}")
            return {
                "error": f"NLU处理失败: {str(e)}",
                "intent": "unknown",
                "user_id": state.get('user_id', 'default_user')
            }
    
    def _should_call_tool(self, state: FinancialAgentState) -> bool:
        """判断是否需要调用工具
        
        Args:
            state: 当前状态
            
        Returns:
            是否需要调用工具
        """
        # 定义需要调用工具的意图
        tool_intents = {
            "query_stock_price",
            "specific_stock",  # 添加查询特定股票的意图
            "stock_historical_data",  # 添加查询股票历史数据的意图
            "query_market_index",
            "query_financial_news",
            "query_economic_data"
        }
        
        need_tool = state.get("intent") in tool_intents
        logger.info(f"是否需要调用工具: {need_tool}, 意图: {state.get('intent')}")
        
        # 更新思考过程
        thinking_process = state.get('thinking_process', [])
        thinking_process.append({
            "step": "decision",
            "description": "判断是否需要调用工具",
            "details": f"意图: {state.get('intent')}, 是否需要工具: {need_tool}",
            "timestamp": datetime.now().isoformat()
        })
        
        # 更新状态中的思考过程
        state['thinking_process'] = thinking_process
        
        return need_tool
    
    def _tool_call_node(self, state: FinancialAgentState) -> FinancialAgentState:
        """自定义工具调用节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态，包含工具调用结果
        """
        try:
            # 获取思考过程
            thinking_process = state.get('thinking_process', [])
            intent = state.get("intent")
            entities = state.get("entities", {})
            logger.info(f"工具调用节点执行, 意图: {intent}, 实体: {entities}")
            
            thinking_process.append({
                "step": "tool_call",
                "description": "开始工具调用",
                "details": f"意图: {intent}, 实体: {entities}",
                "timestamp": datetime.now().isoformat()
            })
            
            # 根据意图选择对应的工具调用方法
            if intent in self.tool_map:
                tool_result = self.tool_map[intent](entities, state)
                
                thinking_process.append({
                    "step": "tool_call",
                    "description": "工具调用完成",
                    "details": f"工具: {intent}, 结果: {tool_result}",
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "tool_result": tool_result,
                    "thinking_process": thinking_process,
                    "user_id": state.get('user_id', 'default_user')
                }
            else:
                logger.warning(f"没有找到对应的工具调用方法, 意图: {intent}")
                thinking_process.append({
                    "step": "tool_call",
                    "description": "工具调用失败",
                    "details": f"没有找到对应的工具调用方法, 意图: {intent}",
                    "timestamp": datetime.now().isoformat()
                })
                return {
                    "tool_result": {"error": f"没有找到对应的工具调用方法, 意图: {intent}"},
                    "thinking_process": thinking_process,
                    "user_id": state.get('user_id', 'default_user')
                }
        except Exception as e:
            logger.error(f"工具调用节点处理失败: {e}")
            return {"tool_result": {"error": str(e)}, "user_id": state.get('user_id', 'default_user')}
    
    def _call_get_stock_price(self, entities: List, state: FinancialAgentState) -> Dict:
        """调用获取股票价格工具
        
        Args:
            entities: 识别的实体列表
            state: 当前状态
            
        Returns:
            工具调用结果
        """
        try:
            # 收集所有识别到的股票实体
            stock_identifiers = []
            
            # 遍历实体列表查找所有股票相关信息
            for entity in entities:
                if entity.get("type") in ["stock_name", "stock"]:
                    stock_name = entity.get("value") or entity.get("name")
                    if stock_name:
                        stock_identifiers.append(stock_name)
                elif entity.get("type") in ["stock_code", "stock"]:
                    stock_code = entity.get("value")
                    if stock_code:
                        stock_identifiers.append(stock_code)
            
            # 如果没有直接识别到，从用户输入中提取（简单处理）
            if not stock_identifiers:
                # 简单的股票名称提取逻辑
                user_input = state.get("user_input", "")
                # 这里可以添加更复杂的股票名称提取逻辑
                logger.warning(f"没有识别到股票名称或代码, 用户输入: {user_input}")
                return {"error": "没有识别到股票名称或代码"}
            
            # 查找对应的工具
            stock_tool = None
            for tool in self.tools:
                if tool.name == "get_stock_price":
                    stock_tool = tool
                    break
            
            if not stock_tool:
                logger.error(f"没有找到get_stock_price工具")
                return {"error": "没有找到get_stock_price工具"}
            
            # 如果只有一个股票，直接返回结果
            if len(stock_identifiers) == 1:
                stock_identifier = stock_identifiers[0]
                logger.info(f"调用获取股票价格工具, 股票: {stock_identifier}")
                return stock_tool.invoke({"stock_name_or_code": stock_identifier})
            
            # 如果有多个股票，返回所有股票的价格信息
            stock_prices = {}
            for stock_identifier in stock_identifiers:
                logger.info(f"调用获取股票价格工具, 股票: {stock_identifier}")
                result = stock_tool.invoke({"stock_name_or_code": stock_identifier})
                if "error" not in result:
                    # 使用股票代码或名称作为键
                    key = result.get("symbol", stock_identifier)
                    stock_prices[key] = result
            
            # 如果有成功获取的股票价格，返回综合结果
            if stock_prices:
                return {
                    "multiple_stocks": True,
                    "stock_prices": stock_prices,
                    "source": "akshare_cache" if any("source" in price and price["source"] == "akshare_cache" for price in stock_prices.values()) else "akshare",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {"error": "无法获取任何股票的价格信息"}
            
        except Exception as e:
            logger.error(f"调用获取股票价格工具失败: {e}")
            return {"error": str(e)}

    def _call_get_stock_historical_data(self, entities: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """调用获取股票历史数据工具
        
        Args:
            entities: 实体列表
            state: 当前状态
            
        Returns:
            Dict: 工具调用结果
        """
        try:
            # 从实体中提取股票名称/代码
            stock_identifiers = []
            for entity in entities:
                if entity.get("type") in ["stock_name", "stock_code"]:
                    stock_identifiers.append(entity.get("value"))
            
            # 如果没有提取到股票信息，使用用户输入作为回退
            if not stock_identifiers:
                user_input = state.get("input", "")
                if user_input:
                    stock_identifiers.append(user_input)
            
            if not stock_identifiers:
                logger.error("无法从输入中提取股票信息")
                return {"error": "无法从输入中提取股票信息"}
            
            # 查找对应的工具
            historical_data_tool = None
            for tool in self.tools:
                if tool.name == "get_stock_historical_data":
                    historical_data_tool = tool
                    break
            
            if not historical_data_tool:
                logger.error(f"没有找到get_stock_historical_data工具")
                return {"error": "没有找到get_stock_historical_data工具"}
            
            # 如果只有一个股票，直接返回结果
            if len(stock_identifiers) == 1:
                stock_identifier = stock_identifiers[0]
                logger.info(f"调用获取股票历史数据工具, 股票: {stock_identifier}")
                result = historical_data_tool.invoke({"stock_name_or_code": stock_identifier})
                
                # 生成K线图、折线图和成交量图
                if "data" in result and result["data"]:
                    try:
                        # 将历史数据转换为DataFrame
                        df = pd.DataFrame(result["data"])
                        logger.info(f"历史数据DataFrame内容: {df}")
                        logger.info(f"历史数据DataFrame列名: {df.columns.tolist()}")
                        
                        # 生成图表
                        if self.chart_generator:
                            kline_chart = self.chart_generator.generate_k_line_chart(stock_identifier, df)
                            line_chart = self.chart_generator.generate_line_chart(stock_identifier, df)
                            volume_chart = self.chart_generator.generate_volume_chart(stock_identifier, df)
                            
                            # 添加图表对象到结果中
                            if kline_chart:
                                result["kline_chart"] = kline_chart
                                logger.info(f"生成K线图成功")
                            if line_chart:
                                result["line_chart"] = line_chart
                                logger.info(f"生成折线图成功")
                            if volume_chart:
                                result["volume_chart"] = volume_chart
                                logger.info(f"生成成交量图成功")
                    except Exception as e:
                        logger.error(f"生成图表失败: {e}")
                        # 即使图表生成失败，也要返回历史数据
                
                return result
            
            # 如果有多个股票，返回所有股票的历史数据信息
            stock_historical_data = {}
            for stock_identifier in stock_identifiers:
                logger.info(f"调用获取股票历史数据工具, 股票: {stock_identifier}")
                result = historical_data_tool.invoke({"stock_name_or_code": stock_identifier})
                if "error" not in result:
                    # 使用股票代码或名称作为键
                    key = result.get("symbol", stock_identifier)
                    stock_historical_data[key] = result
            
            # 如果有成功获取的股票历史数据，返回综合结果
            if stock_historical_data:
                return {
                    "multiple_stocks": True,
                    "stock_historical_data": stock_historical_data,
                    "source": "akshare_cache" if any("source" in data and data["source"] == "akshare_cache" for data in stock_historical_data.values()) else "akshare",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {"error": "无法获取任何股票的历史数据信息"}
            
        except Exception as e:
            logger.error(f"调用获取股票历史数据工具失败: {e}")
            return {"error": str(e)}
    
    def _call_get_market_index(self, entities: Dict, state: FinancialAgentState) -> Dict:
        """调用获取市场指数工具
        
        Args:
            entities: 识别的实体
            state: 当前状态
            
        Returns:
            工具调用结果
        """
        try:
            # 从实体中获取指数名称
            index_name = entities.get("index_name")
            
            # 如果没有识别到，从用户输入中提取（简单处理）
            if not index_name:
                # 简单的指数名称提取逻辑
                user_input = state.get("user_input", "")
                logger.warning(f"没有识别到指数名称, 用户输入: {user_input}")
                return {"error": "没有识别到指数名称"}
            
            logger.info(f"调用获取市场指数工具, 指数: {index_name}")
            
            # 查找对应的工具
            for tool in self.tools:
                if tool.name == "get_market_index":
                    # 调用工具
                    return tool.invoke({"index_name": index_name})
            
            logger.error(f"没有找到get_market_index工具")
            return {"error": "没有找到get_market_index工具"}
            
        except Exception as e:
            logger.error(f"调用获取市场指数工具失败: {e}")
            return {"error": str(e)}
    
    def _call_get_financial_news(self, entities: Dict, state: FinancialAgentState) -> Dict:
        """调用获取财经新闻工具
        
        Args:
            entities: 识别的实体
            state: 当前状态
            
        Returns:
            工具调用结果
        """
        try:
            # 从实体中获取新闻类别
            category = entities.get("category")
            
            logger.info(f"调用获取财经新闻工具, 类别: {category}")
            
            # 查找对应的工具
            for tool in self.tools:
                if tool.name == "get_financial_news":
                    # 调用工具
                    return tool.invoke({"category": category})
            
            logger.error(f"没有找到get_financial_news工具")
            return {"error": "没有找到get_financial_news工具"}
            
        except Exception as e:
            logger.error(f"调用获取财经新闻工具失败: {e}")
            return {"error": str(e)}
    
    def _call_get_economic_data(self, entities: Dict, state: FinancialAgentState) -> Dict:
        """调用获取经济数据工具
        
        Args:
            entities: 识别的实体
            state: 当前状态
            
        Returns:
            工具调用结果
        """
        try:
            # 从实体中获取经济指标
            indicator = entities.get("economic_indicator")
            
            logger.info(f"调用获取经济数据工具, 指标: {indicator}")
            
            # 查找对应的工具
            for tool in self.tools:
                if tool.name == "get_economic_data":
                    # 调用工具
                    return tool.invoke({"indicator": indicator})
            
            logger.error(f"没有找到get_economic_data工具")
            return {"error": "没有找到get_economic_data工具"}
            
        except Exception as e:
            logger.error(f"调用获取经济数据工具失败: {e}")
            return {"error": str(e)}
    
    def _nlg_node(self, state: FinancialAgentState) -> Dict[str, Any]:
        """NLG节点 - 生成自然语言响应
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        try:
            # 获取思考过程
            thinking_process = state.get('thinking_process', [])
            logger.info(f"NLG节点生成响应, 意图: {state.get('intent')}")
            
            thinking_process.append({
                "step": "nlg",
                "description": "开始生成自然语言响应",
                "details": f"意图: {state.get('intent')}",
                "timestamp": datetime.now().isoformat()
            })
            
            # 准备上下文
            context = state.get("context", {})
            
            # 添加工具调用结果到上下文
            if state.get("tool_result"):
                context["realtime_data"] = state["tool_result"]
            
            # 如果有RAG模块，并且意图是查询知识库
            if self.rag and state.get("intent") in ["query_knowledge", "unknown"]:
                # 使用RAG增强生成
                rag_result = self.rag.retrieve_and_generate(state["user_input"])
                if rag_result.get("source_documents"):
                    context["knowledge_base_content"] = rag_result["source_documents"]
                    
                    thinking_process.append({
                        "step": "nlg",
                        "description": "从知识库获取相关信息",
                        "details": f"检索到{len(rag_result.get('source_documents', []))}个相关文档",
                        "timestamp": datetime.now().isoformat()
                    })
            
            # 调用NLG引擎生成响应
            # 构建正确的参数格式
            history = []  # 初始化历史对话列表
            # 如果有会话存储，获取历史对话
            if self.session_storage and hasattr(self.session_storage, 'get_conversation_history'):
                try:
                    # 从会话存储中获取最近的5轮对话
                    raw_history = self.session_storage.get_conversation_history(state.get('user_id', 'default_user'), limit=10)
                    # 将字典列表转换为元组列表，格式为(user_query, bot_response)
                    history = [(item['query'], item['response']) for item in raw_history]
                    logger.info(f"获取到历史对话: {history}")
                    
                    thinking_process.append({
                        "step": "nlg",
                        "description": "获取历史对话上下文",
                        "details": f"已获取最近{len(history)}轮对话",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"获取历史对话失败: {e}")
            
            data_sources = {
                "knowledge_base": context.get("knowledge_base_content", []),
                "realtime_data": context.get("realtime_data", {})
            }
            intent_analysis = {
                "primary_intent": state.get("intent", "unknown"),
                "entities": state.get("entities", {}),
                "resolved_pronouns": state.get("resolved_pronouns", [])
            }
            
            # 构建提示词
            prompt = self.nlg_engine.construct_prompt(
                query=state["user_input"],
                history=history,
                data_sources=data_sources,
                intent_analysis=intent_analysis
            )
            
            logger.info(f"构建的提示词: {prompt[:500]}...")  # 只打印前500个字符用于调试
            
            thinking_process.append({
                "step": "nlg",
                "description": "构建提示词",
                "details": f"提示词长度: {len(prompt)}字符",
                "timestamp": datetime.now().isoformat()
            })
            
            # 调用LLM实际生成回答
            try:
                thinking_process.append({
                    "step": "nlg",
                    "description": "调用LLM生成回答",
                    "details": "正在请求语言模型生成最终响应",
                    "timestamp": datetime.now().isoformat()
                })
                
                response = self.llm_client.generate(prompt=prompt)
                logger.info(f"生成的回答: {response}")
                
                thinking_process.append({
                    "step": "nlg",
                    "description": "生成响应完成",
                    "details": "已获取语言模型的回答",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"调用LLM生成回答失败: {e}")
                response = "抱歉，我暂时无法为您提供帮助。"
                
                thinking_process.append({
                    "step": "nlg",
                    "description": "生成响应失败",
                    "details": f"调用LLM失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "response": response,
                "thinking_process": thinking_process,
                "user_id": state.get('user_id', 'default_user')
            }
            
        except Exception as e:
            logger.error(f"NLG节点处理失败: {e}")
            return {
                "error": f"NLG处理失败: {str(e)}",
                "response": "抱歉，我暂时无法为您提供帮助。",
                "user_id": state.get('user_id', 'default_user')
            }
    
    def run(self, user_input: str, user_id: str = "default_user", config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """运行工作流
        
        Args:
            user_input: 用户输入
            user_id: 用户ID，用于MCP会话存储
            config: LangChain配置
            
        Returns:
            标准化的MCP格式响应
        """
        try:
            logger.info(f"运行工作流, 用户ID: {user_id}, 用户输入: {user_input}")
            
            # 如果有会话存储，获取历史上下文
            history_context = {}
            if self.session_storage:
                try:
                    session_state = self.session_storage.get_session_state(user_id)
                    history_context = session_state.get("context", {})
                except Exception as e:
                    logger.warning(f"获取会话状态失败: {e}")
            
            # 执行工作流
            initial_state = {
                "user_input": user_input,
                "intent": None,
                "entities": None,
                "tool_result": None,
                "response": None,
                "context": history_context,
                "error": None,
                "user_id": user_id,
                "thinking_process": []  # 初始化思考过程
            }
            
            # 执行工作流
            result = self.graph.invoke(initial_state, config=config)
            
            # 更新会话存储中的上下文
            if self.session_storage:
                try:
                    # 获取当前会话状态
                    session_state = self.session_storage.get_session_state(user_id) or {}
                    # 更新上下文和最后交互时间
                    session_state["context"] = result.get("context", {})
                    session_state["last_interaction"] = datetime.now().isoformat()
                    # 保存会话状态
                    self.session_storage.update_session_state(user_id, session_state)
                except Exception as e:
                    logger.warning(f"保存会话状态失败: {e}")
            
            # 标准化MCP响应格式
            mcp_response = {
                "response": result.get("response", "抱歉，我暂时无法为您提供帮助。"),
                "intent": result.get("intent", "unknown"),
                "entities": result.get("entities", {}),
                "context": result.get("context", {}),
                "error": result.get("error"),
                "thinking_process": result.get("thinking_process", []),
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            # 添加图表信息到响应中
            if result.get("intent") == "stock_historical_data" and result.get("tool_result"):
                tool_result = result.get("tool_result", {})
                if "kline_chart" in tool_result:
                    mcp_response["kline_chart"] = tool_result["kline_chart"]
                if "line_chart" in tool_result:
                    mcp_response["line_chart"] = tool_result["line_chart"]
                if "volume_chart" in tool_result:
                    mcp_response["volume_chart"] = tool_result["volume_chart"]
            
            # 如果有会话存储，保存对话历史
            if self.session_storage and hasattr(self.session_storage, 'store_conversation'):
                try:
                    # 保存对话到会话存储
                    self.session_storage.store_conversation(
                        user_id=user_id,
                        user_query=user_input,
                        bot_response=result.get("response", ""),
                        metadata={
                            "intent": result.get("intent", "unknown"),
                            "entities": result.get("entities", {})
                        }
                    )
                    logger.info("对话历史已保存到会话存储")
                except Exception as e:
                    logger.warning(f"保存对话历史失败: {e}")
            
            logger.info(f"工作流运行完成, MCP响应: {mcp_response}")
            return mcp_response
            
            logger.info(f"工作流运行完成, 结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"工作流运行失败: {e}")
            return {
                "response": "抱歉，工作流执行失败。",
                "error": str(e)
            }
