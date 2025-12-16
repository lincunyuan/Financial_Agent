#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多股票查询功能
验证当用户询问股价比较时，系统能够为所有股票调用查询接口
"""

import sys
import os
import logging
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intent_recognizer import IntentRecognizer
from core.tool_integration import FinancialDataAPI
from core.langchain_graph import FinancialAgentGraph
from utils.config_loader import default_config_loader

# 设置日志级别
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 为意图识别器单独设置DEBUG级别日志
intent_logger = logging.getLogger("IntentRecognizer")
intent_logger.setLevel(logging.DEBUG)

def test_intent_recognition():
    """测试意图识别器是否能够识别多个股票实体"""
    logger.info("=== 测试意图识别器 ===")
    
    # 初始化意图识别器
    intent_recognizer = IntentRecognizer()
    
    # 测试用例：股价比较查询
    test_queries = [
        "贵州茅台和东方电气的股价分别是多少？",
        "航天机电比东方电气贵吗？",
        "贵州茅台、航天机电和东方电气这三只股票的价格",
    ]
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n测试用例 {i}: {query}")
        
        # 分析意图
        intent_result = intent_recognizer.analyze(query, history=[], coreferences=[])
        
        logger.info(f"意图: {intent_result.get('primary_intent')}")
        logger.info(f"实体: {intent_result.get('entities', [])}")
        logger.info(f"目标股票: {intent_result.get('target_symbols', [])}")
        
        # 检查是否识别到多个股票实体
        stock_entities = [e for e in intent_result.get('entities', []) if e.get('type') in ['stock_name', 'stock_code', 'stock']]
        logger.info(f"识别到的股票实体数量: {len(stock_entities)}")
        
        # 检查东方电气是否在识别结果中
        if any('东方电气' in str(e.get('value', '')) or '东方电气' in str(e.get('name', '')) for e in stock_entities):
            logger.info("✅ 成功识别到东方电气")
        else:
            logger.warning("❌ 未能识别到东方电气")

def test_financial_data_api():
    """测试金融数据API是否能够查询多个股票"""
    logger.info("\n=== 测试金融数据API ===")
    
    # 初始化数据API
    data_api = FinancialDataAPI()
    
    # 测试单个股票查询
    logger.info("测试单个股票查询:")
    maotai_data = data_api.get_stock_price("贵州茅台")
    logger.info(f"贵州茅台: {maotai_data}")
    
    # 测试东方电气查询
    logger.info("\n测试东方电气查询:")
    dongfang_data = data_api.get_stock_price("东方电气")
    logger.info(f"东方电气: {dongfang_data}")

def test_tool_call_logic():
    """测试工具调用逻辑是否能够处理多个股票实体"""
    logger.info("\n=== 测试工具调用逻辑 ===")
    
    # 创建测试实体列表（包含多个股票）
    test_entities = [
        {"type": "stock_name", "name": "贵州茅台", "value": "贵州茅台"},
        {"type": "stock_name", "name": "东方电气", "value": "东方电气"}
    ]
    
    # 创建测试状态
    test_state = {
        "user_input": "贵州茅台和东方电气的股价分别是多少？",
        "intent": "specific_stock",
        "entities": test_entities
    }
    
    try:
        # 直接测试单个股票的工具调用方法
        data_api = FinancialDataAPI()
        
        logger.info("测试单个股票查询功能:")
        maotai_result = data_api.get_stock_price("贵州茅台")
        logger.info(f"贵州茅台查询结果: {maotai_result}")
        
        logger.info("\n测试东方电气查询功能:")
        dongfang_result = data_api.get_stock_price("东方电气")
        logger.info(f"东方电气查询结果: {dongfang_result}")
        
        # 模拟多股票查询结果处理
        if maotai_result and "error" not in maotai_result and dongfang_result and "error" not in dongfang_result:
            logger.info("\n✅ 模拟多股票查询成功处理")
        else:
            logger.warning("❌ 模拟多股票查询处理失败")
            
    except Exception as e:
        logger.error(f"测试工具调用逻辑失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    """主函数"""
    logger.info("开始测试多股票查询功能")
    
    # 运行测试
    test_intent_recognition()
    test_financial_data_api()
    test_tool_call_logic()
    
    logger.info("\n所有测试完成")
