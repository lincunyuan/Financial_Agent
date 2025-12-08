# 主Agent协调（流程控制与LLM交互）
from typing import Dict, Optional, List
from utils.logging import default_logger as logger
from core.session_manager import RedisSessionManager, build_context_prompt
from core.knowledge_base import FinancialKnowledgeBase
from core.tool_integration import FinancialDataAPI, add_source_citations
from core.llm_client import LLMClient
from utils.config_loader import default_config_loader

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

    def process_query(self, user_id: str, query: str) -> str:
        """处理用户查询的完整流程（增强版）"""
        try:
            # 1. 意图识别和查询分析
            intent_analysis = self._analyze_query_intent(query)
            
            # 2. 如果是简单时间查询，直接返回
            if intent_analysis.get('is_simple_time_query'):
                response = self._handle_simple_time_query(query)
                self.session_manager.store_conversation(user_id, query, response)
                return response
            
            # 3. 获取历史对话
            history = self.session_manager.get_conversation_history(user_id)
            history_tuples = [(turn['query'], turn['response']) for turn in history]
            
            # 4. 根据意图获取相关数据
            relevant_data = self._get_intent_based_data(query, intent_analysis)
            
            # 5. 构建智能提示词
            full_prompt = self._construct_intelligent_prompt(
                query, history_tuples, relevant_data, intent_analysis
            )
            
            # 6. 调用大模型（带重试机制）
            response = self._call_llm_with_retry(full_prompt, intent_analysis)
            
            # 7. 后处理和来源标注
            final_response = self._post_process_response(response, relevant_data, intent_analysis)
            
            # 8. 存储对话历史
            self.session_manager.store_conversation(user_id, query, final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"处理查询失败: {e}")
            return self._get_fallback_response(query, e)

    def _analyze_query_intent(self, query: str) -> Dict:
        """深度意图识别和分析"""
        return self.intent_recognizer.analyze(query)

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
            if intent_analysis.get('needs_real_time_data', False):
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
                for symbol in symbols:
                    tool_data[f"stock_{symbol}"] = self.data_api.get_stock_price(symbol)
                    # 获取详细分析数据
                    tool_data[f"stock_detail_{symbol}"] = self.data_api.get_stock_intraday(symbol)
                    
            elif intent_type == 'economic_analysis':
                # 获取经济数据
                indicators = intent_analysis.get('economic_indicators', ['GDP', 'CPI'])
                for indicator in indicators:
                    tool_data[f"economic_{indicator}"] = self.data_api.get_economic_data(indicator)
                    
        except Exception as e:
            logger.error(f"获取增强工具数据失败: {e}")
            tool_data['error'] = f"数据获取失败: {str(e)}"
            
        return tool_data

    def _construct_intelligent_prompt(self, query: str, history: List[tuple], 
                                    data_sources: Dict, intent_analysis: Dict) -> str:
        """构建智能提示词"""
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
        
        # 2. 添加来源引用
        final_response = self._add_intelligent_citations(processed_response, data_sources)
        
        # 3. 格式优化
        final_response = self._format_response(final_response, intent_analysis)
        
        return final_response

    def _add_intelligent_citations(self, response: str, data_sources: Dict) -> str:
        """智能添加来源引用"""
        citations = []
        
        # 知识库引用
        if data_sources.get('knowledge_base'):
            citations.append("📚 知识库参考")
            
        # 实时数据引用
        if data_sources.get('real_time_data'):
            real_time_sources = []
            for key, data in data_sources['real_time_data'].items():
                if data and not isinstance(data, dict) or data.get('source'):
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