# core/intent_recognizer.py

import re
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class IntentRecognizer:
    """意图识别器 - 深度分析用户查询意图"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
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
        
        # 初始化分词词典（必须在entity_dict定义之后）
        self._init_jieba()

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

    def analyze(self, query: str) -> Dict:
        """深度意图分析"""
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
            'intent_details': {}
        }
        
        try:
            # 1. 关键词匹配评分
            keyword_scores = self._keyword_scoring(query)
            
            # 2. 模式匹配评分
            pattern_scores = self._pattern_matching(query)  # 修复这里
            
            # 3. 实体识别
            entities = self._extract_entities(query)
            if entities:
                analysis['entities'] = entities
                analysis['target_symbols'] = [e['value'] for e in entities if e['type'] == 'stock']
                analysis['target_indices'] = [e['value'] for e in entities if e['type'] == 'index']
            
            # 4. 合并评分
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
            
            self.logger.info(f"意图分析结果: {analysis['primary_intent']} (置信度: {analysis['confidence']:.2f})")
            
        except Exception as e:
            self.logger.error(f"意图分析失败: {e}")
            analysis['error'] = str(e)
        
        return analysis

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
            if entities and intent in ['specific_stock', 'stock_market']:
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