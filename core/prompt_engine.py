# core/prompt_engine.py
from datetime import datetime
from typing import Dict, List, Optional
import logging

# 设置日志
logger = logging.getLogger(__name__)

class PromptEngine:
    """智能提示词引擎"""
    
    def __init__(self, config=None, rag=None):
        """初始化提示词引擎
        
        Args:
            config: 配置项，用于定制提示词生成
            rag: RAG模块，用于检索增强生成
        """
        self.config = config or {}
        self.rag = rag  # 添加RAG模块支持
    
    def construct_prompt(self, query: str, history: List[tuple], 
                         data_sources: Dict, intent_analysis: Dict) -> str:
        """构建智能提示词"""
        
        # 1. 处理代词解析 - 如果有解析后的代词，替换用户查询中的代词
        resolved_query = query
        resolved_pronouns = intent_analysis.get('resolved_pronouns', [])
        if resolved_pronouns:
            logger.info(f"处理代词解析: {resolved_pronouns}")
            # 按代词长度降序排序，避免短代词被长代词包含
            resolved_pronouns.sort(key=lambda x: len(x.get('value', '')), reverse=True)
            for resolved in resolved_pronouns:
                pronoun = resolved.get('pronoun')
                value = resolved.get('value')
                if pronoun and value and pronoun in resolved_query:
                    resolved_query = resolved_query.replace(pronoun, value)
                    logger.info(f"替换代词 '{pronoun}' 为 '{value}'")
        
        # 将resolved_query添加到意图分析结果中
        intent_analysis['resolved_query'] = resolved_query
        
        # 2. 系统角色定义
        system_role = self._get_system_role(intent_analysis)
        
        # 3. 时间上下文
        time_context = self._get_time_context()
        
        # 4. 数据上下文
        data_context = self._format_data_context(data_sources, intent_analysis)
        
        # 5. 历史上下文
        history_context = self._format_history_context(history)
        
        # 6. 回答要求
        response_requirements = self._get_response_requirements(intent_analysis)
        
        prompt = f"""{system_role}

{time_context}

# 可用数据和分析上下文
{data_context}

# 对话历史（最近3轮）
{history_context}

# 当前用户问题
用户：{resolved_query}

# 回答要求
{response_requirements}

请开始回答："""
        
        return prompt
        
    def generate_with_rag(self, query: str, history: List[tuple] = None, 
                         data_sources: Dict = None, intent_analysis: Dict = None) -> Dict:
        """使用RAG生成增强回答
        
        Args:
            query: 用户查询
            history: 对话历史
            data_sources: 数据源
            intent_analysis: 意图分析结果
            
        Returns:
            Dict: 包含回答和来源的字典
        """
        if not self.rag:
            logger.warning("RAG模块未初始化，无法进行检索增强生成")
            # 回退到普通提示词生成
            prompt = self.construct_prompt(query, history or [], 
                                          data_sources or {}, 
                                          intent_analysis or {})
            return {
                "prompt": prompt,
                "has_rag_context": False
            }
        
        try:
            logger.info(f"使用RAG生成增强回答，查询: {query}")
            
            # 使用RAG检索并生成回答
            rag_result = self.rag.retrieve_and_generate(query)
            
            # 如果检索到相关文档，添加到数据源
            if rag_result.get("source_documents"):
                # 构建RAG上下文
                rag_context = [
                    {"content": doc["content"]} 
                    for doc in rag_result['source_documents'][:3]  # 最多使用3个相关文档
                ]
                
                # 更新数据源
                data_sources = data_sources or {}
                data_sources["knowledge_base"] = data_sources.get("knowledge_base", []) + rag_context
                
                # 构建增强提示词
                prompt = self.construct_prompt(query, history or [], 
                                              data_sources, 
                                              intent_analysis or {})
                
                return {
                    "prompt": prompt,
                    "has_rag_context": True,
                    "source_documents": rag_result['source_documents'],
                    "rag_result": rag_result
                }
            else:
                # 如果没有检索到相关文档，使用普通提示词
                prompt = self.construct_prompt(query, history or [], 
                                              data_sources or {}, 
                                              intent_analysis or {})
                return {
                    "prompt": prompt,
                    "has_rag_context": False
                }
                
        except Exception as e:
            logger.error(f"RAG生成失败: {e}")
            # 回退到普通提示词生成
            prompt = self.construct_prompt(query, history or [], 
                                          data_sources or {}, 
                                          intent_analysis or {})
            return {
                "prompt": prompt,
                "has_rag_context": False
            }
    
    def _get_system_role(self, intent_analysis: Dict) -> str:
        """根据意图获取系统角色"""
        roles = {
            'market_news': """你是一名资深财经新闻编辑，擅长从海量信息中提炼关键要点，为投资者提供有价值的市场洞察。""",
            'stock_market': """你是一名专业的证券市场分析师，擅长技术分析和市场趋势判断，能够基于数据提供准确的市场解读。""",
            'specific_stock': """你是一名股票研究专家，精通公司基本面分析和技术面分析，能够提供专业的投资建议。""",
            'economic_analysis': """你是一名宏观经济分析师，擅长解读经济数据背后的含义，预测经济走势。""",
            'investment_advice': """你是一名投资顾问，能够根据市场情况和个人风险偏好提供合理的资产配置建议。""",
            'general': """你是一名专业的金融助手，能够准确回答各类金融相关问题，提供有价值的专业见解。"""
        }
        
        intent = intent_analysis.get('primary_intent', 'general')
        return roles.get(intent, roles['general'])
    
    def _get_time_context(self) -> str:
        """获取当前时间上下文"""
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        return f"当前时间：{current_time}"
    
    def _format_data_context(self, data_sources: Dict, intent_analysis: Dict) -> str:
        """格式化数据上下文"""
        context_parts = []
        
        # 确保data_sources是字典
        if not isinstance(data_sources, dict):
            logger.error(f"data_sources不是字典类型: {type(data_sources)}")
            return "当前无特定数据上下文"
            
        # 实时数据（支持两种键名：'real_time_data'和'realtime_data'）
        real_time_data = data_sources.get('real_time_data', {})
        
        # 确保real_time_data是字典
        if not isinstance(real_time_data, dict):
            logger.error(f"real_time_data不是字典类型: {type(real_time_data)}")
            real_time_data = {}
        else:
            # 合并两种键名的数据
            realtime_data = data_sources.get('realtime_data', {})
            if isinstance(realtime_data, dict):
                real_time_data.update(realtime_data)
        
        if real_time_data:
            context_parts.append("【实时市场数据】")
            
            if 'market_summary' in real_time_data:
                context_parts.append(self._format_market_summary(real_time_data['market_summary']))
                
            if 'financial_news' in real_time_data:
                context_parts.append(self._format_news_summary(real_time_data['financial_news']))
        
        # 检查是否有工具调用结果的实时数据
        tool_result = real_time_data
        if tool_result:
            # 检查是否是多个股票的价格数据
            if tool_result.get('multiple_stocks'):
                if "【实时市场数据】" not in context_parts:
                    context_parts.append("【实时市场数据】")
                
                stock_prices = tool_result.get('stock_prices', {})
                if isinstance(stock_prices, dict):
                    for stock_code, stock_data in stock_prices.items():
                        if isinstance(stock_data, dict):
                            context_parts.append(self._format_stock_price(stock_data))
                            context_parts.append("---")  # 分隔不同股票的数据
                    
                    # 移除最后一个分隔符
                    if context_parts and context_parts[-1] == "---":
                        context_parts.pop()
            # 检查是否是单个股票价格数据
            elif 'symbol' in tool_result and 'price' in tool_result:
                if "【实时市场数据】" not in context_parts:
                    context_parts.append("【实时市场数据】")
                context_parts.append(self._format_stock_price(tool_result))
            # 检查是否是市场指数数据
            elif 'index_name' in tool_result and 'value' in tool_result:
                if "【实时市场数据】" not in context_parts:
                    context_parts.append("【实时市场数据】")
                context_parts.append(self._format_market_index(tool_result))
            # 检查是否是股票历史数据（K线数据）
            elif 'symbol' in tool_result and 'data' in tool_result and tool_result['data']:
                if "【实时市场数据】" not in context_parts:
                    context_parts.append("【实时市场数据】")
                
                import pandas as pd
                try:
                    # 将历史数据转换为DataFrame
                    df = pd.DataFrame(tool_result['data'])
                    
                    # 获取股票名称和代码
                    stock_name = tool_result.get('input_query', '')
                    stock_symbol = tool_result.get('symbol', '未知代码')
                    
                    # 获取最近30天的数据（如果数据不足30天则全部使用）
                    recent_data = df.tail(30) if len(df) > 30 else df
                    
                    # 检查是否有中文列名（收盘价相关）
                    close_price_col = None
                    price_cols = ['close', '收盘价', '收盘', '鏀剁洏']  # 可能的收盘价列名，包括中文乱码情况
                    
                    for col in price_cols:
                        if col in df.columns:
                            close_price_col = col
                            break
                    
                    # 如果找到收盘价列，计算价格区间
                    if close_price_col:
                        recent_min = recent_data[close_price_col].min()
                        recent_max = recent_data[close_price_col].max()
                        current_price = df[close_price_col].iloc[-1] if len(df) > 0 else 0
                        
                        # 构建历史数据统计信息
                        if stock_name:
                            context_parts.append(f"股票：{stock_name} ({stock_symbol})")
                        else:
                            context_parts.append(f"股票代码：{stock_symbol}")
                        
                        context_parts.append(f"当前收盘价：{current_price:.2f}元")
                        context_parts.append(f"近30天价格区间：{recent_min:.2f}元 - {recent_max:.2f}元")
                        # 获取时间范围
                        start_date = end_date = "未知"
                        if '日期' in df.columns:
                            start_date = df['日期'].min()
                            end_date = df['日期'].max()
                        elif 'date' in df.columns:
                            start_date = df['date'].min()
                            end_date = df['date'].max()
                        context_parts.append(f"历史数据时间范围：{start_date} 至 {end_date}")
                except Exception as e:
                    logger.error(f"处理股票历史数据失败: {e}")
            # 检查是否是图表生成结果
            elif 'symbol' in tool_result and 'charts' in tool_result:
                if "【实时市场数据】" not in context_parts:
                    context_parts.append("【实时市场数据】")
                
                # 构建股票信息字符串
                stock_name = tool_result.get('input_query', '')
                stock_symbol = tool_result.get('symbol', '未知代码')
                charts = tool_result.get('charts', {})
                
                if stock_name:
                    context_parts.append(f"股票：{stock_name} ({stock_symbol})")
                else:
                    context_parts.append(f"股票代码：{stock_symbol}")
                
                # 添加图表信息
                context_parts.append("已生成的图表：")
                if 'k_line' in charts:
                    context_parts.append("- K线图已生成")
                if 'line' in charts:
                    context_parts.append("- 价格走势图已生成")
                if 'volume' in charts:
                    context_parts.append("- 成交量图已生成")
        
        # 知识库内容
        knowledge_chunks = data_sources.get('knowledge_base', [])
        if knowledge_chunks:
            context_parts.append("【相关知识背景】")
            for i, chunk in enumerate(knowledge_chunks[:3]):
                text_chunk = chunk.get('text_chunk', chunk.get('content', ''))
                source_info = chunk.get('source', '')
                if source_info:
                    context_parts.append(f"{i+1}. {text_chunk} (来源：{source_info})")
                else:
                    context_parts.append(f"{i+1}. {text_chunk}")
        
        return "\n\n".join(context_parts) if context_parts else "当前无特定数据上下文"
    
    def _format_history_context(self, history: List[tuple]) -> str:
        """格式化历史上下文"""
        if not history:
            return "无历史对话"
        
        history_str = []
        # 只显示最近3轮对话
        for i, (user_msg, assistant_msg) in enumerate(history[-3:], 1):
            history_str.append(f"用户 {i}：{user_msg}")
            history_str.append(f"助手 {i}：{assistant_msg}")
            history_str.append("")
        
        return "\n".join(history_str).strip()
    
    def _get_response_requirements(self, intent_analysis: Dict) -> str:
        """获取回答要求"""
        return """
1. 基于提供的信息和数据进行回答，确保准确性。
2. 保持语言简洁明了，避免使用过于专业的术语。
3. 如果没有足够信息回答，请明确说明。
4. 回答应具有实用性和参考价值。
5. 对于时间相关的问题，请结合当前时间上下文进行回答。
"""
    
    def _format_market_summary(self, market_summary: Dict) -> str:
        """格式化市场摘要"""
        if not market_summary:
            return "无市场摘要数据"
        
        summary_parts = []
        for key, value in market_summary.items():
            summary_parts.append(f"{key}：{value}")
        
        return "\n".join(summary_parts)
    
    def _format_news_summary(self, financial_news: List[Dict]) -> str:
        """格式化新闻摘要"""
        if not financial_news:
            return "无财经新闻数据"
        
        news_parts = []
        for i, news in enumerate(financial_news[:5], 1):
            news_parts.append(f"{i}. {news.get('title', '无标题')}")
            if 'source' in news:
                news_parts.append(f"   来源：{news['source']}")
            if 'content' in news:
                news_parts.append(f"   摘要：{news['content'][:100]}...")
            news_parts.append("")
        
        return "\n".join(news_parts).strip()
    
    def _format_stock_price(self, stock_data: Dict) -> str:
        """格式化股票价格数据"""
        if not stock_data:
            return "无股票价格数据"
        
        parts = []
        symbol = stock_data.get('symbol', '未知代码')
        stock_name = stock_data.get('input_query', '')
        price = stock_data.get('price', 0)
        change = stock_data.get('change', 0)  # 已经是百分比形式，无需乘以100
        change_amount = stock_data.get('change_amount', 0)
        volume = stock_data.get('volume', 0)
        timestamp = stock_data.get('timestamp', '')
        
        # 构建股票信息字符串
        stock_info = f"股票：{stock_name} ({symbol})"
        price_info = f"当前价格：{price}元"
        change_info = f"涨跌幅：{change:.2f}% ({change_amount:+}元)"
        volume_info = f"成交量：{volume:,}股"
        
        if stock_name:
            parts.append(stock_info)
        parts.extend([price_info, change_info, volume_info])
        
        if timestamp:
            parts.append(f"更新时间：{timestamp}")
        
        return "\n".join(parts)
    
    def _format_market_index(self, index_data: Dict) -> str:
        """格式化市场指数数据"""
        if not index_data:
            return "无市场指数数据"
        
        parts = []
        index_name = index_data.get('index_name', '未知指数')
        value = index_data.get('value', 0)
        change = index_data.get('change', 0)  # 已经是百分比形式，无需乘以100
        change_amount = index_data.get('change_amount', 0)
        
        parts.extend([
            f"指数：{index_name}",
            f"当前值：{value}",
            f"涨跌幅：{change:.2f}% ({change_amount:+})"
        ])
        
        return "\n".join(parts)