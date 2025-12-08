# core/prompt_engine.py
from datetime import datetime
from typing import Dict, List

class PromptEngine:
    """智能提示词引擎"""
    
    def construct_prompt(self, query: str, history: List[tuple], 
                         data_sources: Dict, intent_analysis: Dict) -> str:
        """构建智能提示词"""
        
        # 1. 系统角色定义
        system_role = self._get_system_role(intent_analysis)
        
        # 2. 时间上下文
        time_context = self._get_time_context()
        
        # 3. 数据上下文
        data_context = self._format_data_context(data_sources, intent_analysis)
        
        # 4. 历史上下文
        history_context = self._format_history_context(history)
        
        # 5. 回答要求
        response_requirements = self._get_response_requirements(intent_analysis)
        
        prompt = f"""{system_role}

{time_context}

# 可用数据和分析上下文
{data_context}

# 对话历史（最近3轮）
{history_context}

# 当前用户问题
用户：{query}

# 回答要求
{response_requirements}

请开始回答："""
        
        return prompt
    
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
        
        # 实时数据
        real_time_data = data_sources.get('real_time_data', {})
        if real_time_data:
            context_parts.append("【实时市场数据】")
            
            if 'market_summary' in real_time_data:
                context_parts.append(self._format_market_summary(real_time_data['market_summary']))
                
            if 'financial_news' in real_time_data:
                context_parts.append(self._format_news_summary(real_time_data['financial_news']))
        
        # 知识库内容
        knowledge_chunks = data_sources.get('knowledge_base', [])
        if knowledge_chunks:
            context_parts.append("【相关知识背景】")
            for i, chunk in enumerate(knowledge_chunks[:3]):
                context_parts.append(f"{i+1}. {chunk.get('content', '')}")
        
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
1. 基于提供的知识和数据进行回答，确保准确性。
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