# core/intent_recognizer.py

import re
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Tuple, Any
import logging

# 导入LangChain相关模块
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from utils.config_loader import default_config_loader

logger = logging.getLogger(__name__)

class IntentRecognizer:
    """意图识别器 - 深度分析用户查询意图"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config_loader = default_config_loader
        
        # 意图模式定义
        self.intent_patterns = {
            'market_news': {
                'keywords': ['新闻', '要闻', '资讯', '动态', '消息', '头条', '快讯'],
                'patterns': [
                    r'.*今日.*财经.*新闻',
                    r'.*最新.*市场.*动态',
                    r'.*有什么.*新闻',
                    r'.*财经.*消息',
                    r'.*市场.*资讯'
                ],
                'needs_real_time_data': True,
                'needs_knowledge_base': True,
                'priority': 0.9
            },
            'stock_market': {
                'keywords': ['股市', '大盘', '行情', '指数', 'A股', '沪深', '涨跌', '走势'],
                'patterns': [
                    r'.*今天.*股市',
                    r'.*大盘.*走势',
                    r'.*指数.*表现',
                    r'.*A股.*如何',
                    r'.*市场.*行情',
                    r'.*涨.*还是.*跌'
                ],
                'needs_real_time_data': True,
                'target_indices': ['上证指数', '深证成指', '创业板指'],
                'priority': 0.8
            },
            'specific_stock': {
                'keywords': ['茅台', '腾讯', '苹果', '股票', '股价', '个股', '代码'],
                'patterns': [
                    r'.*(\w+)(股票|股价|行情)',
                    r'.*(\w+).*(多少|价格)',
                    r'.*代码.*(\d+)',
                    r'.*(\w+).*(涨|跌)'
                ],
                'needs_real_time_data': True,
                'entity_extraction': True,
                'priority': 0.7
            },
            'stock_historical_data': {
                'keywords': ['历史', '日K', 'K线', '走势', '历史数据', '历史行情', '过往表现', '图表', '走势图'],
                'patterns': [
                    r'.*(\w+).*历史.*(K线|数据|走势|行情)',
                    r'.*(\w+).*日K.*(线|数据|图表)',
                    r'.*(\w+).*过往.*(表现|走势)',
                    r'.*(\w+).*(历史|过去).*价格',
                    r'.*(\w+).*走势图',
                    r'.*(\w+).*图表'
                ],
                'needs_historical_data': True,
                'needs_real_time_data': True,  # 添加这个设置以启用实时数据获取（图表生成）
                'entity_extraction': True,
                'priority': 0.8  # 提高优先级，确保历史数据查询意图优先匹配
            },
            'economic_analysis': {
                'keywords': ['GDP', 'CPI', '经济', '通胀', '利率', '货币政策', '宏观经济'],
                'patterns': [
                    r'.*经济.*数据',
                    r'.*GDP.*增长',
                    r'.*CPI.*如何',
                    r'.*通胀.*情况',
                    r'.*利率.*政策'
                ],
                'needs_real_time_data': True,
                'economic_indicators': ['GDP', 'CPI', 'PPI'],
                'priority': 0.6
            },
            'investment_advice': {
                'keywords': ['建议', '推荐', '买什么', '投资', '配置', '操作', '策略'],
                'patterns': [
                    r'.*投资.*建议',
                    r'.*买.*什么.*股票',
                    r'.*如何.*配置',
                    r'.*操作.*策略',
                    r'.*推荐.*个股'
                ],
                'needs_historical_context': True,
                'needs_knowledge_base': True,
                'priority': 0.5
            },
            'time_query': {
                'keywords': ['今天', '现在', '日期', '时间', '周几', '星期'],
                'patterns': [
                    r'.*今天.*几号',
                    r'.*现在.*几点',
                    r'.*星期.*几',
                    r'.*周.*几',
                    r'.*什么.*时间'
                ],
                'is_simple_time_query': True,
                'priority': 0.3
            }
        }
        
        # 实体词典
        self.entity_dict = {
            'stocks': {
                '茅台': '600519.SS', '贵州茅台': '600519.SS',
                '腾讯': '00700.HK', '腾讯控股': '00700.HK',
                '苹果': 'AAPL.US', '苹果公司': 'AAPL.US',
                '阿里巴巴': 'BABA.US', '阿里': 'BABA.US',
                '微软': 'MSFT.US', '谷歌': 'GOOGL.US',
                '亚马逊': 'AMZN.US', '特斯拉': 'TSLA.US',
                '宁德时代': '300750.SZ', '比亚迪': '002594.SZ'
            },
            'indices': {
                '上证指数': '000001.SS', '上证': '000001.SS',
                '深证成指': '399001.SZ', '深证': '399001.SZ',
                '创业板指': '399006.SZ', '创业板': '399006.SZ',
                '沪深300': '000300.SS', '沪深': '000300.SS',
                '科创50': '000688.SS', '科创': '000688.SS',
                '道指': 'DJI', '道琼斯': 'DJI',
                '纳指': 'IXIC', '纳斯达克': 'IXIC',
                '标普': 'SPX', '标普500': 'SPX'
            }
        }
        
        # 加载股票映射文件
        self._load_stock_mapping()
        
        # 初始化分词词典（必须在entity_dict定义之后）
        self._init_jieba()
        
        # 初始化LangChain组件
        self._init_langchain_components()
        
        # 检查LangChain组件的初始化状态
        self.logger.info(f"LangChain组件状态: llm={self.llm is not None}, intent_prompt={self.intent_prompt is not None}, entity_prompt={self.entity_prompt is not None}")
        self.logger.info("意图识别器初始化完成")

    def _load_stock_mapping(self):
        """加载股票映射文件到实体词典"""
        import csv
        import os
        
        try:
            # 获取股票映射文件路径
            stock_mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'stock_mapping.csv')
            
            if os.path.exists(stock_mapping_path):
                with open(stock_mapping_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # 跳过表头
                    
                    # 统计加载的股票数量
                    stock_count = 0
                    
                    for row in reader:
                        if len(row) >= 2:
                            stock_name = row[0].strip()
                            stock_code = row[1].strip()
                            
                            # 修复股票代码格式 - 去除可能的sh/sz前缀
                            if stock_code.startswith(('sh', 'sz')):
                                stock_code = stock_code[2:]
                            
                            # 确保股票代码格式正确
                            if not stock_code.endswith(('.SS', '.SZ', '.HK', '.US')):
                                # 根据A股代码规则添加交易所后缀
                                if stock_code.startswith(('0', '3')):
                                    stock_code += '.SZ'
                                elif stock_code.startswith('6'):
                                    stock_code += '.SS'
                            
                            # 添加到实体词典
                            self.entity_dict['stocks'][stock_name] = stock_code
                            stock_count += 1
                    
                    self.logger.info(f"成功加载 {stock_count} 只股票到实体词典")
            else:
                self.logger.warning(f"股票映射文件不存在: {stock_mapping_path}")
                
        except Exception as e:
            self.logger.error(f"加载股票映射文件失败: {e}")
    
    def _init_jieba(self):
        """初始化中文分词"""
        try:
            # 添加金融领域词典
            financial_terms = list(self.entity_dict['stocks'].keys()) + list(self.entity_dict['indices'].keys())
            for term in financial_terms:
                jieba.add_word(term)
            
            # 添加自定义词典
            custom_words = ['财经新闻', '股市行情', '投资建议', '经济数据', '货币政策']
            for word in custom_words:
                jieba.add_word(word)
                
        except Exception as e:
            self.logger.warning(f"初始化分词词典失败: {e}")
    
    def _init_langchain_components(self):
        """初始化LangChain组件"""
        try:
            # 加载LLM配置
            llm_config = self.config_loader.load_config("model_config.yaml")
            self.logger.debug(f"加载的LLM配置: {llm_config}")
            
            # 创建ChatOpenAI实例
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=llm_config.get("model", "qwen-plus"),
                temperature=0.1,
                openai_api_base=llm_config.get("base_url"),
                openai_api_key=llm_config.get("api_key")
            )
            self.logger.debug(f"LLM客户端创建成功: {self.llm}")
            
            # 1. 意图定义PromptTemplate
            self.intent_prompt = PromptTemplate(
                template="""
                你是一个金融领域的意图识别专家。请根据用户的查询和历史对话上下文，识别出主要意图。
                
                可用意图列表：
                - market_news: 查询财经新闻
                - stock_market: 查询股市行情
                - specific_stock: 查询特定股票
                - stock_historical_data: 查询股票历史数据或K线图
                - economic_analysis: 查询经济数据分析
                - investment_advice: 查询投资建议
                - time_query: 查询时间信息
                - general: 一般性问题
                
                重要提示：
                1. 如果当前查询中包含代词（如"它"、"这个"、"那个"等），请根据历史对话上下文确定其具体指代的实体
                2. 务必考虑历史对话中的金融实体（如股票名称、代码等），理解用户的完整意图
                3. 当用户查询股票的历史数据、日K线、K线图等时，应识别为stock_historical_data意图
                
                历史对话（如果有）：
                {history}
                
                当前用户查询: {query}
                
                请以JSON格式返回识别结果，包含以下字段：
                - intent: 识别出的主要意图
                - confidence: 置信度（0-1之间的数字）
                """,
                input_variables=["query", "history"]
            )
            
            # 2. JSON实体抽取PromptTemplate
            self.entity_prompt = PromptTemplate(
                template="你是一个金融领域的实体识别专家。请从用户的查询和历史对话上下文中提取出金融相关的实体。\n\n重要规则：\n1. 必须仔细分析历史对话上下文，特别是前一轮对话中提到的金融实体\n2. 如果当前查询中包含代词（如\"它\"、\"这个\"、\"那个\"等），请根据历史对话上下文明确指出其具体指代的实体名称\n3. 例如，如果上一轮对话提到\"贵州茅台\"，当前查询问\"它的市值是多少？\"，则应提取实体{{'type': 'stock_name', 'value': '贵州茅台'}}\n\n实体类型包括：\n- stock_name: 股票名称\n- stock_code: 股票代码\n- index_name: 指数名称\n- time: 时间信息\n- economic_indicator: 经济指标\n\n历史对话（如果有）：\n{history}\n\n当前用户查询: {query}\n\n请以JSON格式返回识别结果，包含以下字段：\n- entities: 实体列表，每个实体包含type和value字段\n",
                input_variables=["query", "history"]
            )
            
            # 创建JSON输出解析器
            self.json_parser = JsonOutputParser()
            
            self.logger.info("LangChain组件初始化成功")
            
        except Exception as e:
            self.logger.error(f"LangChain组件初始化失败: {e}", exc_info=True)
            self.llm = None
            self.intent_prompt = None
            self.entity_prompt = None

    def analyze(self, query: str, history: List[Dict] = None, coreferences: List[Dict] = None) -> Dict:
        """深度意图分析"""
        history = history or []
        coreferences = coreferences or []
        analysis = {
            'primary_intent': 'general',
            'confidence': 0.0,
            'entities': [],
            'needs_real_time_data': False,
            'needs_knowledge_base': True,
            'needs_historical_context': False,
            'is_simple_time_query': False,
            'target_symbols': [],
            'target_indices': [],
            'keywords': [],
            'intent_details': {},
            'langchain_used': False,
            'resolved_pronouns': []  # 新增字段：存储解析后的代词
        }
        
        try:
            # 1. 检查是否有代词需要解析
            has_pronoun = any(pronoun in query for pronoun in ['它', '这个', '那个', '其', '该'])
            
            # 2. 优先使用存储的指代关系进行代词解析
            resolved_entities = []
            if has_pronoun:
                resolved_entities = self._resolve_pronouns_with_coreferences(query, coreferences, history)
                if resolved_entities:
                    self.logger.info(f"使用存储的指代关系解析代词成功: {resolved_entities}")
                    analysis['resolved_pronouns'] = resolved_entities  # 存储解析结果
                    analysis['entities'] = resolved_entities  # 将解析出的实体添加到分析结果中
            
            # 3. 如果没有存储的指代关系或解析失败，尝试使用LangChain进行意图识别
            langchain_used = False
            if not resolved_entities and ((self.llm and self.intent_prompt and self.entity_prompt) or has_pronoun):
                # 如果有存储的指代关系，将其添加到历史对话中，以便LangChain可以使用
                formatted_coreferences = ""
                if coreferences:
                    for coref in coreferences:
                        formatted_coreferences += f"代词'{coref.get('pronoun')}'指代'{coref.get('value')}'({coref.get('type')})\n"
                
                langchain_result = self._analyze_with_langchain(query, history, coreferences=formatted_coreferences)
                if langchain_result:
                    analysis.update(langchain_result)
                    langchain_used = True
                    analysis['langchain_used'] = True
                    self.logger.info(f"LangChain意图分析结果: {analysis['primary_intent']} (置信度: {analysis['confidence']:.2f})")
            
            # 初始化entities变量，确保在所有分支中都有定义
            entities = []
            
            # 4. 如果LangChain不可用或没有返回结果，使用传统方法
            if not langchain_used:
                self.logger.info("使用传统方法进行意图分析")
                
                # 1. 关键词匹配评分
                keyword_scores = self._keyword_scoring(query)
                
                # 2. 模式匹配评分
                pattern_scores = self._pattern_matching(query)
                
                # 3. 实体识别 - 包含代词解析
                entities = self._extract_entities(query)
                
                # 如果解析出了指代实体，将其与当前查询中提取的其他实体合并
                if resolved_entities:
                    # 将解析出的代词实体与当前查询中提取的其他实体合并
                    entities.extend(resolved_entities)
                    # 去重：如果同一实体被多次识别，只保留一个
                    seen = set()
                    unique_entities = []
                    for entity in entities:
                        key = (entity.get('type'), entity.get('value'))
                        if key not in seen:
                            seen.add(key)
                            unique_entities.append(entity)
                    entities = unique_entities
                    analysis['entities'] = entities
            
            # 如果当前查询包含代词且没有直接识别到实体，尝试从历史对话中获取
            if has_pronoun and not analysis.get('entities') and not entities:
                self.logger.info(f"检测到代词但没有直接识别到实体，从历史对话中提取: {history}")
                for item in reversed(history):
                    # 处理不同格式的历史对话
                    if isinstance(item, dict):
                        # 字典格式: {'query': ..., 'response': ..., 'metadata': ...}
                        dialogue = item
                        # 从历史对话的metadata中提取实体
                        if 'metadata' in dialogue and 'entities' in dialogue['metadata']:
                            metadata_entities = dialogue['metadata']['entities']
                            if metadata_entities:
                                entities = metadata_entities
                                self.logger.info(f"从历史对话metadata中提取到实体: {entities}")
                                break
                        # 如果metadata中没有实体，尝试从历史查询和响应中提取
                        user_msg = dialogue.get('query', '')
                        bot_msg = dialogue.get('response', '')
                    else:
                        # 元组格式: (user_msg, bot_msg)
                        user_msg, bot_msg = item
                    
                    # 从历史用户消息中提取实体
                    prev_entities = self._extract_entities(user_msg)
                    if prev_entities:
                        entities = prev_entities
                        self.logger.info(f"从历史用户消息中提取到实体: {entities}")
                        break
                    # 从历史助手响应中提取实体
                    prev_entities = self._extract_entities(bot_msg)
                    if prev_entities:
                        entities = prev_entities
                        self.logger.info(f"从历史助手响应中提取到实体: {entities}")
                        break
            
            if entities:
                analysis['entities'] = entities
                analysis['target_symbols'] = [e['value'] for e in entities if e['type'] == 'stock']
                analysis['target_indices'] = [e['value'] for e in entities if e['type'] == 'index']
            
            # 4. 合并评分 - 确保在所有代码路径中都定义了评分变量
            if 'keyword_scores' not in locals():
                keyword_scores = self._keyword_scoring(query)
            if 'pattern_scores' not in locals():
                pattern_scores = self._pattern_matching(query)
            
            combined_scores = self._combine_scores(keyword_scores, pattern_scores, entities)
            
            # 5. 确定主要意图
            if combined_scores:
                primary_intent, confidence = max(combined_scores.items(), key=lambda x: x[1])
                if confidence > 0.3:  # 置信度阈值
                    analysis['primary_intent'] = primary_intent
                    analysis['confidence'] = confidence
                    
                    # 合并意图配置
                    intent_config = self.intent_patterns.get(primary_intent, {})
                    for key in ['needs_real_time_data', 'needs_knowledge_base', 
                               'needs_historical_context', 'is_simple_time_query']:
                        if key in intent_config:
                            analysis[key] = intent_config[key]
                    
                    # 设置特定目标
                    if primary_intent == 'stock_market' and 'target_indices' in intent_config:
                        analysis['target_indices'] = intent_config['target_indices']
                    elif primary_intent == 'economic_analysis' and 'economic_indicators' in intent_config:
                        analysis['economic_indicators'] = intent_config['economic_indicators']
            
            # 6. 提取关键词
            analysis['keywords'] = self._extract_keywords(query)
            
            self.logger.info(f"传统意图分析结果: {analysis['primary_intent']} (置信度: {analysis['confidence']:.2f})")
            
            # 生成解析后的查询（替换代词）
            resolved_query = query
            resolved_pronouns = analysis.get('resolved_pronouns', [])
            if resolved_pronouns:
                # 按代词长度降序排序，避免短代词被长代词包含
                resolved_pronouns.sort(key=lambda x: len(x.get('value', '')), reverse=True)
                for resolved in resolved_pronouns:
                    pronoun = resolved.get('pronoun')
                    value = resolved.get('value')
                    if pronoun and value and pronoun in resolved_query:
                        resolved_query = resolved_query.replace(pronoun, value)
                        self.logger.info(f"替换代词 '{pronoun}' 为 '{value}'")
            analysis['resolved_query'] = resolved_query
        except Exception as e:
            self.logger.error(f"意图分析失败: {e}")
            analysis['error'] = str(e)
            analysis['resolved_query'] = query  # 即使出错，也要返回原始查询
        
        return analysis
    
    def _resolve_pronouns_with_coreferences(self, query: str, coreferences: List[Dict], history: List[Dict] = None) -> List[Dict]:
        """使用存储的指代关系进行代词解析
        
        Args:
            query: 用户查询
            coreferences: 指代关系列表
            history: 历史对话
            
        Returns:
            List[Dict]: 解析后的实体列表
        """
        resolved_entities = []
        
        # 1. 从查询中提取代词
        pronouns = [pronoun for pronoun in ['它', '这个', '那个', '其', '该'] if pronoun in query]
        
        if not pronouns:
            return resolved_entities
            
        # 2. 根据代词过滤指代关系
        filtered_coreferences = []
        for pronoun in pronouns:
            for coref in coreferences:
                if coref.get('pronoun') == pronoun:
                    filtered_coreferences.append(coref)
        
        # 3. 按时间倒序排序（优先使用最近的指代关系）
        filtered_coreferences.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 4. 应用就近原则，选择最近的指代关系
        for coref in filtered_coreferences:
            # 获取当前指代关系的代词
            pronoun = coref.get('pronoun')
            
            # 创建实体对象，包含pronoun字段
            entity = {
                'pronoun': pronoun,  # 添加代词字段
                'value': coref.get('value'),
                'type': coref.get('type', 'stock'),
                'start_pos': query.find(pronoun),
                'end_pos': query.find(pronoun) + len(pronoun),
                'confidence': 0.95,  # 较高的置信度，因为是从存储的指代关系中解析的
                'code': coref.get('value'),
                'name': coref.get('value')  # 添加名称字段
            }
            resolved_entities.append(entity)
            
            # 如果已经解析了所有代词，停止
            if len(resolved_entities) >= len(pronouns):
                break
                
        return resolved_entities

    def _analyze_with_langchain(self, query: str, history: List[Tuple] = None, coreferences: str = "") -> Dict:
        """使用LangChain进行意图分析和实体提取"""
        try:
            result = {}
            
            # 将历史对话格式化为易读的文本形式
            formatted_history = ""
            if coreferences:
                formatted_history += f"【代词指代关系】\n{coreferences}\n"
            
            if history:
                for i, item in enumerate(history):
                    # 处理不同格式的历史对话
                    if isinstance(item, dict):
                        # 字典格式: {'query': ..., 'response': ..., 'metadata': ...}
                        user_msg = item.get('query', '')
                        bot_msg = item.get('response', '')
                    else:
                        # 元组格式: (user_msg, bot_msg)
                        user_msg, bot_msg = item
                    formatted_history += f"用户[{i+1}]: {user_msg}\n助手[{i+1}]: {bot_msg}\n"
            
            # 1. 意图识别 - 包含历史对话上下文
            context = {"query": query, "history": formatted_history}
            intent_chain = self.intent_prompt | self.llm | self.json_parser
            intent_result = intent_chain.invoke(context)
            
            result['primary_intent'] = intent_result.get('intent', 'general')
            result['confidence'] = intent_result.get('confidence', 0.0)
            
            # 2. 实体提取 - 包含历史对话上下文
            context = {"query": query, "history": formatted_history}
            entity_chain = self.entity_prompt | self.llm | self.json_parser
            entity_result = entity_chain.invoke(context)
            
            entities = entity_result.get('entities', [])
            result['entities'] = entities
            
            # 3. 转换实体格式并设置目标符号
            result['target_symbols'] = []
            result['target_indices'] = []
            
            for entity in entities:
                entity_type = entity.get('type')
                value = entity.get('value')
                
                if entity_type in ['stock_name', 'stock_code']:
                    # 转换为系统内部的股票代码格式
                    if entity_type == 'stock_name' and value in self.entity_dict['stocks']:
                        result['target_symbols'].append(self.entity_dict['stocks'][value])
                    elif entity_type == 'stock_code':
                        # 确保股票代码格式正确
                        if len(value) == 6 and value.isdigit():
                            # 正确的交易所映射：000开头、002开头、300开头为深交所(.SZ)，600开头为上交所(.SS)
                            result['target_symbols'].append(f"{value}.SZ" if value.startswith(('000', '002', '300')) else f"{value}.SS")
                
                elif entity_type == 'index_name' and value in self.entity_dict['indices']:
                    result['target_indices'].append(self.entity_dict['indices'][value])
            
            # 4. 设置意图相关的配置
            intent_config = self.intent_patterns.get(result['primary_intent'], {})
            for key in ['needs_real_time_data', 'needs_knowledge_base', 
                       'needs_historical_context', 'is_simple_time_query']:
                if key in intent_config:
                    result[key] = intent_config[key]
            
            # 设置特定目标
            if result['primary_intent'] == 'stock_market' and 'target_indices' in intent_config:
                result['target_indices'] = intent_config['target_indices']
            elif result['primary_intent'] == 'economic_analysis' and 'economic_indicators' in intent_config:
                result['economic_indicators'] = intent_config['economic_indicators']
            
            # 5. 提取关键词
            result['keywords'] = self._extract_keywords(query)
            
            return result
            
        except Exception as e:
            self.logger.error(f"使用LangChain进行意图分析失败: {e}")
            return None

    def _keyword_scoring(self, query: str) -> Dict[str, float]:
        """关键词匹配评分"""
        scores = {}
        query_lower = query.lower()
        
        for intent, config in self.intent_patterns.items():
            score = 0
            total_keywords = len(config['keywords'])
            
            for keyword in config['keywords']:
                if keyword in query_lower:
                    score += 1
            
            if score > 0:
                # 归一化评分
                normalized_score = score / total_keywords
                # 应用意图优先级权重
                weighted_score = normalized_score * config.get('priority', 0.5)
                scores[intent] = weighted_score
        
        return scores

    def _pattern_matching(self, query: str) -> Dict[str, float]:
        """模式匹配评分 - 新增方法"""
        scores = {}
        
        for intent, config in self.intent_patterns.items():
            max_pattern_score = 0
            
            for pattern in config.get('patterns', []):
                try:
                    if re.search(pattern, query, re.IGNORECASE):
                        # 模式匹配成功，给予较高分数
                        pattern_score = 0.7  # 基础分
                        
                        # 根据模式复杂度调整分数
                        if len(pattern) > 20:  # 复杂模式
                            pattern_score += 0.2
                        elif '.*' in pattern:  # 通用模式
                            pattern_score += 0.1
                            
                        max_pattern_score = max(max_pattern_score, pattern_score)
                        
                except re.error as e:
                    self.logger.warning(f"正则表达式错误 {pattern}: {e}")
                    continue
            
            if max_pattern_score > 0:
                # 应用意图优先级权重
                weighted_score = max_pattern_score * config.get('priority', 0.5)
                scores[intent] = weighted_score
        
        return scores

    def _extract_entities(self, query: str) -> List[Dict]:
        """实体识别"""
        entities = []
        
        try:
            # 使用jieba进行分词和词性标注
            words = pseg.cut(query)
            
            for word, flag in words:
                # 识别股票
                if word in self.entity_dict['stocks']:
                    entities.append({
                        'type': 'stock',
                        'value': self.entity_dict['stocks'][word],
                        'name': word,
                        'source': '词典匹配',
                        'confidence': 0.9
                    })
                
                # 识别指数
                elif word in self.entity_dict['indices']:
                    entities.append({
                        'type': 'index', 
                        'value': self.entity_dict['indices'][word],
                        'name': word,
                        'source': '词典匹配',
                        'confidence': 0.9
                    })
                
                # 识别数字代码（股票代码模式）
                elif flag == 'm' and len(word) >= 4 and word.isdigit():
                    # 简单判断是否为股票代码
                    if len(word) == 6:  # A股代码
                        entities.append({
                            'type': 'stock_code',
                            'value': word + '.SS' if word.startswith(('0', '3')) else word + '.SZ',
                            'name': f'股票{word}',
                            'source': '数字识别',
                            'confidence': 0.6
                        })
        
        except Exception as e:
            self.logger.warning(f"实体识别失败: {e}")
        
        return entities

    def _combine_scores(self, keyword_scores: Dict, pattern_scores: Dict, entities: List) -> Dict[str, float]:
        """合并各种评分"""
        combined = {}
        all_intents = set(keyword_scores.keys()) | set(pattern_scores.keys())
        
        for intent in all_intents:
            keyword_score = keyword_scores.get(intent, 0)
            pattern_score = pattern_scores.get(intent, 0)
            
            # 加权合并
            combined_score = (keyword_score * 0.6 + pattern_score * 0.4)
            
            # 实体增强
            if entities and intent in ['specific_stock', 'stock_market', 'stock_historical_data']:
                entity_boost = min(len(entities) * 0.1, 0.3)  # 每个实体增加0.1，最多0.3
                combined_score += entity_boost
            
            combined[intent] = min(combined_score, 1.0)  # 限制最大为1.0
        
        return combined

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        try:
            # 使用TF-IDF思路提取重要词汇
            words = jieba.cut(query)
            word_freq = {}
            
            for word in words:
                if len(word) > 1:  # 过滤单字
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 按频率排序，取前5个
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, freq in sorted_words[:5]]
            
        except Exception as e:
            self.logger.warning(f"关键词提取失败: {e}")
        
        return keywords

    def get_intent_description(self, intent: str) -> str:
        """获取意图描述"""
        descriptions = {
            'market_news': '财经新闻查询',
            'stock_market': '股市行情分析', 
            'specific_stock': '个股信息查询',
            'economic_analysis': '经济数据分析',
            'investment_advice': '投资建议咨询',
            'time_query': '时间信息查询',
            'general': '一般性问题'
        }
        return descriptions.get(intent, '未知意图')

    def validate_intent(self, intent_analysis: Dict, query: str) -> bool:
        """验证意图分析结果"""
        if not intent_analysis:
            return False
        
        # 检查必要字段
        required_fields = ['primary_intent', 'confidence']
        if not all(field in intent_analysis for field in required_fields):
            return False
        
        # 检查置信度合理性
        confidence = intent_analysis.get('confidence', 0)
        if not 0 <= confidence <= 1:
            return False
        
        # 检查意图类型有效性
        intent = intent_analysis.get('primary_intent')
        if intent not in self.intent_patterns and intent != 'general':
            return False
        
        return True

# 使用示例
if __name__ == "__main__":
    # 测试意图识别器
    recognizer = IntentRecognizer()
    
    test_queries = [
        "今天股市怎么样？",
        "贵州茅台股价多少？", 
        "最新的财经新闻有哪些？",
        "GDP增长情况如何？",
        "现在几点了？"
    ]
    
    for query in test_queries:
        result = recognizer.analyze(query)
        print(f"查询: {query}")
        print(f"意图: {result['primary_intent']} (置信度: {result['confidence']:.2f})")
        print(f"实体: {[e['name'] for e in result['entities']]}")
        print("-" * 50)