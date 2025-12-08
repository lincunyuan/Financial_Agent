# core/data_processor.py

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器 - 负责响应后处理和数据整合"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 数据验证规则
        self.validation_rules = {
            'stock_price': {
                'required_fields': ['price', 'change', 'timestamp'],
                'numeric_fields': ['price', 'change', 'volume'],
                'range_checks': {
                    'change': (-50, 50),  # 涨跌幅范围 -50% 到 50%
                    'price': (0, 100000)  # 价格范围
                }
            },
            'market_index': {
                'required_fields': ['price', 'change', 'name'],
                'numeric_fields': ['price', 'change', 'volume']
            },
            'news_article': {
                'required_fields': ['title', 'source', 'publishedAt'],
                'text_fields': ['title', 'description']
            }
        }

    def integrate_data_into_response(self, response: str, data_sources: Dict, 
                                   intent_analysis: Dict) -> str:
        """
        将数据整合到LLM响应中，确保数据准确性和一致性
        """
        try:
            # 1. 验证和清理数据
            validated_data = self._validate_data_sources(data_sources)
            
            # 2. 根据意图类型进行数据整合
            intent_type = intent_analysis.get('primary_intent', 'general')
            
            if intent_type == 'market_news':
                return self._integrate_news_data(response, validated_data)
            elif intent_type == 'stock_market':
                return self._integrate_market_data(response, validated_data)
            elif intent_type == 'specific_stock':
                return self._integrate_stock_data(response, validated_data)
            elif intent_type == 'economic_analysis':
                return self._integrate_economic_data(response, validated_data)
            else:
                return self._integrate_general_data(response, validated_data)
                
        except Exception as e:
            self.logger.error(f"数据整合失败: {e}")
            return response  # 返回原始响应作为降级方案

    def _validate_data_sources(self, data_sources: Dict) -> Dict:
        """验证数据源的有效性和完整性"""
        validated_data = {
            'knowledge_base': [],
            'real_time_data': {},
            'historical_context': {},
            'warnings': []
        }
        
        # 验证知识库数据
        if 'knowledge_base' in data_sources:
            validated_data['knowledge_base'] = self._validate_knowledge_data(
                data_sources['knowledge_base']
            )
        
        # 验证实时数据
        if 'real_time_data' in data_sources:
            validated_data['real_time_data'], warnings = self._validate_real_time_data(
                data_sources['real_time_data']
            )
            validated_data['warnings'].extend(warnings)
        
        # 验证历史上下文
        if 'historical_context' in data_sources:
            validated_data['historical_context'] = data_sources['historical_context']
        
        return validated_data

    def _validate_knowledge_data(self, knowledge_data: List[Dict]) -> List[Dict]:
        """验证知识库数据"""
        validated = []
        
        for chunk in knowledge_data:
            if not isinstance(chunk, dict):
                continue
                
            # 检查必要字段
            if chunk.get('content') and len(chunk['content']) > 10:
                # 清理内容格式
                cleaned_chunk = chunk.copy()
                cleaned_chunk['content'] = self._clean_text(chunk['content'])
                validated.append(cleaned_chunk)
        
        return validated[:5]  # 限制数量

    def _validate_real_time_data(self, real_time_data: Dict) -> tuple:
        """验证实时数据"""
        validated_data = {}
        warnings = []
        
        for key, data in real_time_data.items():
            if data is None:
                warnings.append(f"{key}: 数据为空")
                continue
                
            try:
                if key.startswith('stock_'):
                    validated = self._validate_stock_data(data, key)
                    if validated:
                        validated_data[key] = validated
                    else:
                        warnings.append(f"{key}: 股票数据验证失败")
                        
                elif key.startswith('index_'):
                    validated = self._validate_index_data(data, key)
                    if validated:
                        validated_data[key] = validated
                    else:
                        warnings.append(f"{key}: 指数数据验证失败")
                        
                elif key == 'financial_news':
                    validated = self._validate_news_data(data, key)
                    if validated:
                        validated_data[key] = validated
                    else:
                        warnings.append(f"{key}: 新闻数据验证失败")
                        
                elif key == 'market_summary':
                    validated = self._validate_market_summary(data, key)
                    if validated:
                        validated_data[key] = validated
                    else:
                        warnings.append(f"{key}: 市场概况验证失败")
                        
            except Exception as e:
                warnings.append(f"{key}: 验证异常 - {str(e)}")
        
        return validated_data, warnings

    def _validate_stock_data(self, data: Dict, data_key: str) -> Optional[Dict]:
        """验证股票数据"""
        if not isinstance(data, dict):
            return None
            
        # 基本验证
        required = self.validation_rules['stock_price']['required_fields']
        if not all(field in data for field in required):
            return None
            
        # 数值验证
        validated_data = data.copy()
        for field in self.validation_rules['stock_price']['numeric_fields']:
            if field in data and data[field] is not None:
                try:
                    # 转换数值类型
                    if isinstance(data[field], str):
                        # 处理百分比和货币符号
                        value_str = str(data[field]).replace('%', '').replace(',', '')
                        validated_data[field] = float(value_str)
                    else:
                        validated_data[field] = float(data[field])
                except (ValueError, TypeError):
                    validated_data[field] = None
        
        # 范围检查
        range_checks = self.validation_rules['stock_price']['range_checks']
        for field, (min_val, max_val) in range_checks.items():
            if field in validated_data and validated_data[field] is not None:
                if not (min_val <= validated_data[field] <= max_val):
                    self.logger.warning(f"{data_key} {field} 值异常: {validated_data[field]}")
                    validated_data[field] = None  # 标记为无效
        
        return validated_data

    def _validate_index_data(self, data: Dict, data_key: str) -> Optional[Dict]:
        """验证指数数据"""
        return self._validate_stock_data(data, data_key)  # 复用股票验证逻辑

    def _validate_news_data(self, data: Dict, data_key: str) -> Optional[Dict]:
        """验证新闻数据"""
        if not isinstance(data, dict) or 'articles' not in data:
            return None
            
        validated_articles = []
        for article in data.get('articles', []):
            if isinstance(article, dict) and article.get('title'):
                # 清理文章数据
                cleaned_article = {
                    'title': self._clean_text(article.get('title', '')),
                    'description': self._clean_text(article.get('description', '')[:200]),  # 限制长度
                    'source': article.get('source', '未知来源'),
                    'publishedAt': self._format_timestamp(article.get('publishedAt')),
                    'url': article.get('url', '')
                }
                validated_articles.append(cleaned_article)
        
        return {
            'articles': validated_articles[:10],  # 限制数量
            'total': len(validated_articles),
            'timestamp': datetime.now().isoformat()
        }

    def _validate_market_summary(self, data: Dict, data_key: str) -> Optional[Dict]:
        """验证市场概况数据"""
        if not isinstance(data, dict):
            return None
            
        validated = data.copy()
        
        # 确保必要字段存在
        if 'major_indices' not in validated:
            validated['major_indices'] = {}
        if 'market_activity' not in validated:
            validated['market_activity'] = {}
            
        return validated

    def _integrate_news_data(self, response: str, validated_data: Dict) -> str:
        """整合新闻数据到响应中"""
        news_data = validated_data.get('real_time_data', {}).get('financial_news')
        
        if not news_data or not news_data.get('articles'):
            return response + "\n\n📰 今日暂无重要财经新闻更新。"
        
        # 提取关键新闻标题
        articles = news_data['articles'][:3]  # 取前3条
        news_summary = "📰 今日财经要闻：\n"
        
        for i, article in enumerate(articles, 1):
            news_summary += f"{i}. {article['title']}\n"
        
        # 检查响应中是否已包含新闻内容
        if '新闻' not in response and '要闻' not in response:
            return response + "\n\n" + news_summary
        else:
            # 如果响应已包含新闻，则补充具体内容
            return response.replace("今日财经新闻", "今日财经新闻（详情如下）") + "\n" + news_summary

    def _integrate_market_data(self, response: str, validated_data: Dict) -> str:
        """整合市场数据到响应中"""
        market_data = validated_data.get('real_time_data', {})
        
        # 构建市场数据摘要
        market_summary = self._build_market_summary(market_data)
        
        if not market_summary:
            return response + "\n\n📊 当前市场数据暂不可用。"
        
        # 检查响应中是否已包含市场数据
        if any(keyword in response for keyword in ['涨', '跌', '指数', '点', '大盘']):
            # 响应已包含市场分析，补充具体数据
            lines = response.split('\n')
            enhanced_lines = []
            
            for line in lines:
                if any(keyword in line for keyword in ['指数', '涨跌']):
                    # 在相关行后插入具体数据
                    enhanced_lines.append(line)
                    if '上证指数' in market_summary:
                        enhanced_lines.append(market_summary)
                        market_summary = ""  # 避免重复插入
                else:
                    enhanced_lines.append(line)
            
            if market_summary:  # 如果还有未插入的数据
                enhanced_lines.append("\n📊 市场数据详情：" + market_summary)
                
            return '\n'.join(enhanced_lines)
        else:
            return response + "\n\n📊 市场数据概况：" + market_summary

    def _integrate_stock_data(self, response: str, validated_data: Dict) -> str:
        """整合股票数据到响应中"""
        real_time_data = validated_data.get('real_time_data', {})
        
        # 提取股票数据
        stock_data = {}
        for key, data in real_time_data.items():
            if key.startswith('stock_') and data:
                symbol = key.replace('stock_', '')
                stock_data[symbol] = data
        
        if not stock_data:
            return response + "\n\n💹 当前股票数据暂不可用。"
        
        # 构建股票数据表格
        stock_table = self._build_stock_table(stock_data)
        
        # 将数据整合到响应中
        if any(symbol in response for symbol in stock_data.keys()):
            # 股票数据已提及，插入具体数值
            return self._insert_stock_data_into_response(response, stock_data, stock_table)
        else:
            # 补充股票数据
            return response + "\n\n💹 相关股票数据：\n" + stock_table

    def _integrate_economic_data(self, response: str, validated_data: Dict) -> str:
        """整合经济数据到响应中"""
        economic_data = validated_data.get('real_time_data', {})
        
        economic_indicators = []
        for key, data in economic_data.items():
            if key.startswith('economic_') and data:
                indicator = key.replace('economic_', '')
                economic_indicators.append((indicator, data))
        
        if not economic_indicators:
            return response + "\n\n📈 当前经济数据暂不可用。"
        
        # 构建经济数据摘要
        economic_summary = "📈 相关经济指标：\n"
        for indicator, data in economic_indicators:
            if data.get('data'):
                latest_value = data['data'][-1] if data['data'] else {}
                value_str = str(latest_value.get('value', 'N/A'))
                economic_summary += f"- {indicator}: {value_str}\n"
        
        return response + "\n\n" + economic_summary

    def _integrate_general_data(self, response: str, validated_data: Dict) -> str:
        """整合通用数据到响应中"""
        # 简单的数据补充逻辑
        enhanced_response = response
        
        # 如果有知识库数据，确保响应中引用了相关内容
        knowledge_chunks = validated_data.get('knowledge_base', [])
        if knowledge_chunks and len(response) > 100:
            # 在响应末尾添加知识参考
            enhanced_response += "\n\n💡 以上分析基于相关金融知识和市场规律。"
        
        return enhanced_response

    def _build_market_summary(self, market_data: Dict) -> str:
        """构建市场数据摘要"""
        summary_parts = []
        
        # 主要指数
        major_indices = []
        for key, data in market_data.items():
            if key.startswith('index_') and data:
                index_name = key.replace('index_', '')
                price = data.get('price', 'N/A')
                change = data.get('change', 'N/A')
                major_indices.append(f"{index_name}: {price} ({change}%)")
        
        if major_indices:
            summary_parts.append("📊 主要指数: " + " | ".join(major_indices))
        
        # 市场概况
        market_summary = market_data.get('market_summary', {})
        if market_summary.get('market_activity'):
            activity = market_summary['market_activity']
            rising = activity.get('rising_companies', 'N/A')
            falling = activity.get('falling_companies', 'N/A')
            summary_parts.append(f"📈 市场热度: 上涨{rising}家 | 下跌{falling}家")
        
        return "\n".join(summary_parts) if summary_parts else ""

    def _build_stock_table(self, stock_data: Dict) -> str:
        """构建股票数据表格"""
        if not stock_data:
            return ""
        
        table_lines = []
        header = "股票名称     当前价格     涨跌幅     成交量"
        table_lines.append(header)
        table_lines.append("-" * 40)
        
        for symbol, data in stock_data.items():
            name = data.get('name', symbol)
            price = data.get('price', 'N/A')
            change = data.get('change', 'N/A')
            volume = self._format_volume(data.get('volume', 0))
            
            table_lines.append(f"{name:8} {price:10} {change:8}% {volume:12}")
        
        return "\n".join(table_lines)

    def _insert_stock_data_into_response(self, response: str, stock_data: Dict, stock_table: str) -> str:
        """将股票数据插入到响应中的适当位置"""
        lines = response.split('\n')
        enhanced_lines = []
        data_inserted = False
        
        for line in lines:
            enhanced_lines.append(line)
            
            # 在提到具体股票的行后插入数据
            for symbol in stock_data.keys():
                stock_name = stock_data[symbol].get('name', symbol)
                if stock_name in line and not data_inserted:
                    enhanced_lines.append(stock_table)
                    data_inserted = True
                    break
        
        if not data_inserted:
            enhanced_lines.append("\n💹 相关股票数据：\n" + stock_table)
        
        return '\n'.join(enhanced_lines)

    def _clean_text(self, text: str) -> str:
        """清理文本数据"""
        if not text:
            return ""
        
        # 移除多余空格和换行
        cleaned = re.sub(r'\s+', ' ', str(text)).strip()
        # 移除特殊字符但保留中文和基本标点
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff%，。！？：；（）《》]', '', cleaned)
        return cleaned

    def _format_timestamp(self, timestamp: Any) -> str:
        """格式化时间戳"""
        if not timestamp:
            return "未知时间"
        
        try:
            if isinstance(timestamp, str):
                # 尝试解析各种时间格式
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(timestamp[:19], fmt)
                        return dt.strftime('%Y年%m月%d日 %H:%M')
                    except ValueError:
                        continue
            return str(timestamp)
        except:
            return "时间格式异常"

    def _format_volume(self, volume: Any) -> str:
        """格式化成交量"""
        try:
            vol = int(volume)
            if vol >= 100000000:  # 1亿
                return f"{vol/100000000:.2f}亿"
            elif vol >= 10000:  # 1万
                return f"{vol/10000:.2f}万"
            else:
                return str(vol)
        except (ValueError, TypeError):
            return "N/A"

    def add_data_quality_indicators(self, response: str, data_sources: Dict) -> str:
        """添加数据质量指示器"""
        quality_indicators = []
        
        real_time_data = data_sources.get('real_time_data', {})
        if real_time_data:
            # 计算实时数据覆盖率
            valid_data_count = sum(1 for data in real_time_data.values() if data)
            total_data_count = len(real_time_data)
            coverage = valid_data_count / total_data_count if total_data_count > 0 else 0
            
            if coverage > 0.8:
                quality_indicators.append("✅ 数据完整性: 优秀")
            elif coverage > 0.5:
                quality_indicators.append("⚠️ 数据完整性: 良好")
            else:
                quality_indicators.append("❌ 数据完整性: 待改善")
        
        knowledge_data = data_sources.get('knowledge_base', [])
        if knowledge_data:
            quality_indicators.append(f"📚 知识参考: {len(knowledge_data)}条")
        
        if quality_indicators:
            return response + "\n\n" + " | ".join(quality_indicators)
        
        return response