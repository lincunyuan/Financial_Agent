# 主Agent协调（流程控制与LLM交互）
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logging import default_logger as logger
from core.session_manager import RedisSessionManager, build_context_prompt
from core.knowledge_base import FinancialKnowledgeBase
from core.tool_integration import FinancialDataAPI, add_source_citations
from core.llm_client import LLMClient
from utils.config_loader import default_config_loader
from core.chart_generator import ChartGenerator

# 导入自定义模块
from core.session_manager import RedisSessionManager
from core.knowledge_base import FinancialKnowledgeBase
from core.tool_integration import FinancialDataAPI, add_source_citations
from core.llm_client import LLMClient
from utils.config_loader import default_config_loader

# 导入新增的智能模块
from core.intent_recognizer import IntentRecognizer
from core.prompt_engine import PromptEngine
from core.data_processor import DataProcessor
from utils.text_processing import insert_current_time, format_prompt_with_context

# 导入市场数据API
from core.mcp import MarketDataAPI, StockDataAPI, NewsAPI, EconomicDataAPI, call_plugin

class FinancialAssistantAgent:
    def __init__(self, config_dir: str = "config"):
        """初始化Agent组件"""
        self.config_loader = default_config_loader
        
        # 加载数据库配置
        db_config = self.config_loader.load_config("database.yaml")
        
        # 初始化会话管理器
        redis_host = self.config_loader.get("database.yaml", "redis.host", "localhost")
        redis_port = self.config_loader.get("database.yaml", "redis.port", 6379)
        self.session_manager = RedisSessionManager(host=redis_host, port=redis_port)
        
        # 初始化知识库
        mysql_config = self.config_loader.get("database.yaml", "mysql", {})
        self.knowledge_base = FinancialKnowledgeBase(
            mysql_host=mysql_config.get("host", "localhost"),
            mysql_user=mysql_config.get("user", "root"),
            mysql_password=mysql_config.get("password", ""),
            mysql_db=mysql_config.get("database", "financial_rag")
        )
        
        # 初始化数据API
        api_keys_config = self.config_loader.load_config("api_keys.yaml")
        self.data_api = FinancialDataAPI(api_keys=api_keys_config)
        
        # 初始化LLM客户端
        self.llm_client = LLMClient()
        
        # 初始化意图识别器
        self.intent_recognizer = IntentRecognizer()
        
        # 初始化智能提示词构建器
        self.prompt_engine = PromptEngine()
        
        # 初始化数据处理器
        self.data_processor = DataProcessor()
        
        # 初始化图表生成器
        self.chart_generator = ChartGenerator()

    def process_query(self, user_id: str, query: str) -> dict:
        """处理用户查询的完整流程（增强版）"""
        try:
            # 1. 获取历史对话
            history = self.session_manager.get_conversation_history(user_id)
            logger.info(f"历史对话类型: {type(history)}, 长度: {len(history)}")
            
            # 2. 意图识别和查询分析
            intent_analysis = self._analyze_query_intent(user_id, query, history)
            logger.info(f"意图分析结果类型: {type(intent_analysis)}, 内容: {intent_analysis}")
            
            # 2. 如果是简单时间查询，直接返回
            if intent_analysis.get('is_simple_time_query'):
                response = self._handle_simple_time_query(query)
                self.session_manager.store_conversation(user_id, query, response)
                return {
                    "response": response,
                    "intent": "time_query",
                    "user_id": user_id
                }
            
            # 使用解析后的查询（如果有）
            resolved_query = intent_analysis.get('resolved_query', query)
            logger.info(f"解析后的查询：{resolved_query}")
            
            # 3. 准备历史对话数据
            history_tuples = [(turn['query'], turn['response']) for turn in history]
            
            # 4. 根据意图获取相关数据
            relevant_data = self._get_intent_based_data(resolved_query, intent_analysis)
            logger.info(f"相关数据类型: {type(relevant_data)}, 内容: {relevant_data}")
            
            # 确保相关数据是字典类型
            if not isinstance(relevant_data, dict):
                logger.error(f"相关数据类型错误: {type(relevant_data)}, 内容: {relevant_data}")
                relevant_data = {}
            
            # 调试信息
            logger.info(f"意图分析结果: {intent_analysis}")
            logger.info(f"相关数据结构: {relevant_data}")
            
            # 5. 构建智能提示词
            full_prompt = self._construct_intelligent_prompt(
                resolved_query, history_tuples, relevant_data, intent_analysis
            )
            logger.info(f"构建的提示词长度: {len(full_prompt)}")
            
            # 6. 调用大模型（带重试机制）
            response = self._call_llm_with_retry(full_prompt, intent_analysis)
            logger.info(f"大模型响应类型: {type(response)}, 内容: {response}")
            
            # 7. 后处理和来源标注
            final_response = self._post_process_response(response, relevant_data, intent_analysis)
            
            # 8. 存储对话历史
            self.session_manager.store_conversation(user_id, query, final_response)
            
            # 9. 存储指代关系
            logger.info(f"意图分析结果：resolved_pronouns={intent_analysis.get('resolved_pronouns')}, entities={intent_analysis.get('entities')}")
            
            # 如果有解析出的代词，存储解析结果
            if intent_analysis.get('resolved_pronouns'):
                for resolved in intent_analysis['resolved_pronouns']:
                    logger.info(f"存储代词指代关系：user_id={user_id}, pronoun={resolved.get('pronoun')}, type={resolved.get('type')}, target={resolved.get('target')}, value={resolved.get('value')}")
                    self.session_manager.store_coreference(
                        user_id,
                        pronoun=resolved.get('pronoun'),
                        referent_type=resolved.get('type', 'entity'),
                        referent_target=resolved.get('target', 'stock'),
                        referent_value=resolved.get('value')
                    )
            # 如果没有解析出的代词，但识别到了实体，为可能的后续代词（如"它"）存储指代关系
            elif intent_analysis.get('entities'):
                logger.info(f"没有解析出代词，但识别到实体：{intent_analysis['entities']}")
                for entity in intent_analysis['entities']:
                    # 同时检查两种可能的字段名：'type'和'entity_type'
                    entity_type = entity.get('type') or entity.get('entity_type')
                    logger.info(f"实体类型：{entity_type}")
                    # 检查实体类型是否与我们支持的类型匹配
                    if entity_type in ['stock', 'index', 'company', 'stock_name', 'stock_code', 'index_name', 'index_code']:
                        logger.info(f"实体类型匹配：{entity_type}")
                        # 统一实体类型为内部使用的类型
                        internal_type = 'stock' if entity_type in ['stock_name', 'stock_code'] else 'index' if entity_type in ['index_name', 'index_code'] else entity_type
                        # 获取实体值，优先使用value字段，如果没有则使用name字段
                        entity_value = entity.get('value') or entity.get('name')
                        logger.info(f"存储代词'它'的指代关系：user_id={user_id}, type={internal_type}, target={entity_type}, value={entity_value}")
                        self.session_manager.store_coreference(
                            user_id,
                            pronoun='它',  # 为最常用的代词创建指代关系
                            referent_type=internal_type,
                            referent_target=entity_type,
                            referent_value=entity_value
                        )
                    else:
                        logger.info(f"实体类型不匹配：{entity_type}")
            else:
                logger.info("没有解析出代词，也没有识别到实体")
            
            # 构建响应字典
            response_dict = {
                "response": final_response,
                "intent": intent_analysis.get('primary_intent', 'general'),
                "entities": intent_analysis.get('entities', []),
                "user_id": user_id
            }
            
            # 如果是K线图查询，添加图表路径
            if intent_analysis.get('primary_intent') == 'stock_historical_data':
                real_time_data = relevant_data.get('real_time_data', {})
                if "kline_chart" in real_time_data:
                    response_dict["kline_chart"] = real_time_data["kline_chart"]
                if "line_chart" in real_time_data:
                    response_dict["line_chart"] = real_time_data["line_chart"]
                if "volume_chart" in real_time_data:
                    response_dict["volume_chart"] = real_time_data["volume_chart"]
            
            return response_dict
            
        except Exception as e:
            logger.exception(f"处理查询失败的详细信息: {e}")
            return {
                "response": self._get_fallback_response(query, e),
                "error": str(e),
                "intent": "error",
                "user_id": user_id
            }

    def _analyze_query_intent(self, user_id: str, query: str, history: List[Dict]) -> Dict:
        """深度意图识别和分析"""
        # 获取指代关系
        coreferences = self.session_manager.get_coreferences(user_id)
        intent_analysis = self.intent_recognizer.analyze(query, history=history, coreferences=coreferences)
        # 确保resolved_query被包含在意图分析结果中
        if 'resolved_query' not in intent_analysis:
            intent_analysis['resolved_query'] = query
        return intent_analysis

    def _get_intent_based_data(self, query: str, intent_analysis: Dict) -> Dict:
        """根据意图获取相关数据"""
        data_sources = {
            'knowledge_base': [],
            'real_time_data': {},
            'historical_context': {}
        }
        
        intent_type = intent_analysis.get('primary_intent', 'general')
        
        try:
            # 1. 检索知识库内容
            if intent_analysis.get('needs_knowledge_base', True):
                data_sources['knowledge_base'] = self.knowledge_base.retrieve_relevant_chunks(
                    query, 
                    top_k=intent_analysis.get('knowledge_limit', 5)
                )
            
            # 2. 获取实时数据
            if intent_analysis.get('needs_real_time_data', False) or intent_analysis.get('primary_intent') == 'stock_historical_data':
                data_sources['real_time_data'] = self._get_enhanced_tool_data(query, intent_analysis)
            
            # 3. 获取历史上下文
            if intent_analysis.get('needs_historical_context', False):
                data_sources['historical_context'] = self._get_historical_context(intent_analysis)
                
        except Exception as e:
            logger.error(f"获取意图数据失败: {e}")
            data_sources['error'] = str(e)
            
        return data_sources

    def _get_enhanced_tool_data(self, query: str, intent_analysis: Dict) -> Dict:
        """增强的工具数据获取（基于意图）"""
        tool_data = {}
        intent_type = intent_analysis.get('primary_intent')
        
        try:
            logger.info(f"_get_enhanced_tool_data被调用，意图类型：{intent_type}")
            if intent_type == 'market_news':
                # 获取财经新闻
                news_query = intent_analysis.get('news_keywords', '财经')
                tool_data["financial_news"] = self.data_api.get_financial_news(
                    query=news_query, 
                    limit=intent_analysis.get('news_limit', 8)
                )
                
            elif intent_type == 'stock_market':
                # 获取市场概况
                tool_data["market_summary"] = self.data_api.get_today_market_summary()
                
                # 获取主要指数
                indices = intent_analysis.get('target_indices', ['上证指数', '深证成指'])
                for index in indices:
                    tool_data[f"index_{index}"] = self.data_api.get_market_index(index)
                    
            elif intent_type == 'specific_stock':
                # 获取特定股票数据
                symbols = intent_analysis.get('target_symbols', [])
                if len(symbols) > 0:
                    # 如果只有一个股票，使用单股票格式
                    if len(symbols) == 1:
                        symbol = symbols[0]
                        stock_data = self.data_api.get_stock_price(symbol)
                        tool_data.update(stock_data)
                    # 如果有多个股票，使用多股票格式
                    else:
                        tool_data['multiple_stocks'] = True
                        tool_data['stock_prices'] = {}
                        for symbol in symbols:
                            stock_data = self.data_api.get_stock_price(symbol)
                            stock_key = stock_data.get('symbol', symbol)
                            tool_data['stock_prices'][stock_key] = stock_data
                    tool_data['source'] = 'akshare_cache' if 'source' in tool_data and tool_data['source'] == 'akshare_cache' else 'akshare'
                    tool_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
            elif intent_type == 'economic_analysis':
                # 获取经济数据
                indicators = intent_analysis.get('economic_indicators', ['GDP', 'CPI'])
                for indicator in indicators:
                    tool_data[f"economic_{indicator}"] = self.data_api.get_economic_data(indicator)
                    
            elif intent_type == 'stock_historical_data':
                logger.info(f"处理stock_historical_data意图，意图分析：{intent_analysis}")
                # 获取历史K线数据
                symbols = intent_analysis.get('target_symbols', [])
                logger.info(f"目标股票代码：{symbols}")
                
                # 如果target_symbols为空，尝试从entities中提取
                if not symbols:
                    logger.info("target_symbols为空，尝试从entities中提取")
                    entities = intent_analysis.get('entities', [])
                    logger.info(f"entities：{entities}")
                    
                    for entity in entities:
                        entity_type = entity.get('type')
                        entity_value = entity.get('value')
                        logger.info(f"检查实体：类型={entity_type}, 值={entity_value}")
                        
                        if entity_type in ['stock_name', 'stock_code']:
                            symbols.append(entity_value)
                        elif entity_type in ['index_name', 'index_code']:
                            symbols.append(entity_value)
                
                logger.info(f"最终目标符号：{symbols}")
                if len(symbols) > 0:
                    symbol = symbols[0]
                    # 默认获取最近30天的数据
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    
                    historical_data = self.data_api.get_historical_data(
                        stock_code=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        interval="1d"
                    )
                    logger.info(f"获取的历史数据：{historical_data}")
                    
                    # 检查历史数据是否有效
                    logger.info(f"historical_data内容: {historical_data}")
                    # 转换为DataFrame以便生成图表
                    import pandas as pd
                    df = pd.DataFrame()
                    
                    if historical_data.get('data'):
                        df = pd.DataFrame(historical_data['data'])
                        logger.info(f"历史数据转换为DataFrame成功，行数: {len(df)}")
                    else:
                        logger.warning(f"historical_data中没有data字段或data为空")
                        # 创建一个空的DataFrame，包含必要的列
                        df = pd.DataFrame({
                            '日期': pd.date_range(end=datetime.now(), periods=10),
                            '开盘': [3400] * 10,
                            '最高': [3410] * 10,
                            '最低': [3390] * 10,
                            '收盘': [3400] * 10,
                            '成交量': [10000000] * 10
                        })
                        logger.info(f"创建了一个空的DataFrame，行数: {len(df)}")
                    
                    # 先将历史数据更新到工具数据中
                    tool_data.update(historical_data)
                    
                    try:
                        print(f"\n=== 开始生成图表 ===")
                        print(f"股票代码: {symbol}")
                        print(f"DataFrame内容:\n{df}")
                        print(f"DataFrame列名: {df.columns.tolist()}")
                        
                        # 生成K线图
                        print("\n--- 生成K线图 ---")
                        kline_chart_path = self.chart_generator.generate_k_line_chart(
                            stock_code=symbol,
                            historical_data=df,
                            title=f"{symbol} 近30天K线图"
                        )
                        print(f"K线图生成结果: {kline_chart_path}")
                        
                        # 生成收盘价折线图
                        print("\n--- 生成折线图 ---")
                        line_chart_path = self.chart_generator.generate_line_chart(
                            stock_code=symbol,
                            historical_data=df,
                            title=f"{symbol} 近30天收盘价走势"
                        )
                        print(f"折线图生成结果: {line_chart_path}")
                        
                        # 生成成交量图
                        print("\n--- 生成成交量图 ---")
                        volume_chart_path = self.chart_generator.generate_volume_chart(
                            stock_code=symbol,
                            historical_data=df,
                            title=f"{symbol} 近30天成交量"
                        )
                        print(f"成交量图生成结果: {volume_chart_path}")
                        
                        # 添加图表路径到工具数据（会覆盖historical_data中的空值）
                        tool_data['kline_chart'] = kline_chart_path
                        tool_data['line_chart'] = line_chart_path
                        tool_data['volume_chart'] = volume_chart_path
                        tool_data['symbol'] = symbol
                        print(f"图表路径已添加到tool_data: {tool_data}")
                        print("\n=== 图表生成完成 ===")
                    except Exception as e:
                        logger.error(f"生成图表失败: {e}")
                    logger.info(f"工具数据最终结构: {tool_data}")
                else:
                    logger.warning("没有找到有效的股票代码")
        except Exception as e:
            logger.error(f"获取增强工具数据失败: {e}")
            tool_data['error'] = f"数据获取失败: {str(e)}"
            
        return tool_data

    def _construct_intelligent_prompt(self, query: str, history: List[tuple], 
                                    data_sources: Dict, intent_analysis: Dict) -> str:
        """构建智能提示词"""
        # 确保data_sources是字典类型
        if not isinstance(data_sources, dict):
            logger.error(f"data_sources类型错误: {type(data_sources)}, 内容: {data_sources}")
            data_sources = {}
        
        return self.prompt_engine.construct_prompt(
            query=query,
            history=history,
            data_sources=data_sources,
            intent_analysis=intent_analysis
        )

    def _call_llm_with_retry(self, prompt: str, intent_analysis: Dict, max_retries: int = 3) -> str:
        """带重试机制的LLM调用"""
        for attempt in range(max_retries):
            try:
                response = self.llm_client.generate(prompt)
                
                # 验证响应质量
                if self._validate_response_quality(response, intent_analysis):
                    return response
                else:
                    logger.warning(f"LLM响应质量不佳，第{attempt+1}次重试")
                    # 优化提示词后重试
                    prompt = self._enhance_prompt_for_retry(prompt, attempt)
                    
            except Exception as e:
                logger.error(f"LLM调用失败（第{attempt+1}次）: {e}")
                if attempt == max_retries - 1:
                    raise e
                    
        return "抱歉，暂时无法生成满意的回答。"

    def _validate_response_quality(self, response: str, intent_analysis: Dict) -> bool:
        """验证响应质量"""
        # 基础验证
        if not response or len(response.strip()) < 10:
            return False
            
        # 意图特定验证
        intent_type = intent_analysis.get('primary_intent')
        if intent_type == 'market_news' and '新闻' not in response:
            return False
        elif intent_type == 'stock_market' and not any(keyword in response for keyword in ['涨', '跌', '指数', '点']):
            return False
            
        return True

    def _post_process_response(self, response: str, data_sources: Dict, intent_analysis: Dict) -> str:
        """响应后处理"""
        # 1. 数据整合和验证
        processed_response = self.data_processor.integrate_data_into_response(
            response, data_sources, intent_analysis
        )
        
        # 2. 添加图表信息
        intent_type = intent_analysis.get('primary_intent')
        if intent_type == 'stock_historical_data':
            real_time_data = data_sources.get('real_time_data', {})
            if 'kline_chart' in real_time_data and real_time_data['kline_chart']:
                processed_response += f"\n\n📊 已生成{real_time_data.get('symbol')}的K线图，文件路径：{real_time_data['kline_chart']}"
            if 'line_chart' in real_time_data and real_time_data['line_chart']:
                processed_response += f"\n📈 已生成{real_time_data.get('symbol')}的收盘价走势图，文件路径：{real_time_data['line_chart']}"
        
        # 3. 添加来源引用
        final_response = self._add_intelligent_citations(processed_response, data_sources)
        
        # 4. 格式优化
        final_response = self._format_response(final_response, intent_analysis)
        
        return final_response

    def _add_intelligent_citations(self, response: str, data_sources: Dict) -> str:
        """智能添加来源引用"""
        citations = []
        
        # 知识库引用
        knowledge_chunks = data_sources.get('knowledge_base', [])
        if knowledge_chunks:
            knowledge_citations = []
            for chunk in knowledge_chunks:
                source_info = chunk.get('source', '')
                if source_info and source_info not in knowledge_citations:
                    knowledge_citations.append(source_info)
            
            if knowledge_citations:
                citations.append(f"📚 参考资料: {', '.join(knowledge_citations)}")
            else:
                citations.append("📚 知识库参考")
            
        # 实时数据引用
        if data_sources.get('real_time_data'):
            real_time_sources = []
            for key, data in data_sources['real_time_data'].items():
                # 确保data是字典类型且包含source键
                if isinstance(data, dict) and data.get('source'):
                    source = data.get('source', '实时数据')
                    real_time_sources.append(source)
            
            if real_time_sources:
                citations.append(f"📊 实时数据: {', '.join(set(real_time_sources))}")
        
        if citations:
            return response + "\n\n" + "\n".join(citations)
        
        return response

    def _handle_simple_time_query(self, query: str) -> str:
        """处理简单时间查询"""
        from utils.text_processing import insert_current_time
        return insert_current_time(query)

    def _format_response(self, response: str, intent_analysis: Dict) -> str:
        """格式化响应输出"""
        # 根据不同意图类型进行响应格式化
        intent_type = intent_analysis.get('primary_intent')
        
        # 市场分析类响应格式
        if intent_type in ['market_news', 'stock_market', 'industry_analysis']:
            response = f"## {intent_type.replace('_', ' ').title()}分析\n\n{response}"
        
        # 投资建议类响应格式
        elif intent_type in ['investment_advice', 'risk_management']:
            response = f"## {intent_type.replace('_', ' ').title()}\n\n⚠️ **风险提示**：投资有风险，决策需谨慎\n\n{response}"
        
        # 财务计算类响应格式
        elif intent_type == 'financial_calculation':
            response = f"## 财务计算结果\n\n{response}"
        
        # 基础信息查询格式
        elif intent_type == 'general':
            response = f"## 信息查询结果\n\n{response}"
        
        return response

    def _get_fallback_response(self, query: str, error: Exception) -> str:
        """降级响应处理"""
        # 基础信息查询
        if any(keyword in query for keyword in ['时间', '日期', '今天', '现在']):
            return self._handle_simple_time_query(query)
            
        # 返回友好的错误信息
        return f"抱歉，处理您的请求时出现了技术问题。错误详情：{str(error)}"

    def close(self):
        """关闭资源连接"""
        self.knowledge_base.close_connections()