#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RAG功能是否正常工作
"""

import sys
import os
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_knowledge_base():
    """测试知识库功能"""
    logger.info("=== 测试知识库功能 ===")
    
    try:
        from core.knowledge_base import FinancialKnowledgeBase
        
        # 创建知识库实例
        kb = FinancialKnowledgeBase()
        logger.info(f"知识库实例创建成功，使用的嵌入模型: {kb.embedding_model_name}")
        
        # 测试向量维度是否正确
        logger.info(f"Milvus集合向量维度: {kb.vector_dim}")
        
        # 测试检索功能
        query = "贵州茅台2024年净利润增长率是多少？"
        logger.info(f"测试检索查询: {query}")
        
        # 获取相关片段
        results = kb.retrieve_relevant_chunks(query, top_k=3)
        logger.info(f"检索结果数量: {len(results)}")
        
        if results:
            logger.info("检索结果详情:")
            for i, result in enumerate(results, 1):
                logger.info(f"  结果 {i}:")
                logger.info(f"    文档ID: {result.get('document_id')}")
                logger.info(f"    文本片段: {result.get('text_chunk')[:100]}...")
                logger.info(f"    相似度分数: {result.get('similarity_score')}")
                logger.info(f"    来源信息: {result.get('source')}")
        else:
            logger.warning("未检索到相关结果")
        
        return True
        
    except Exception as e:
        logger.error(f"知识库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_engine():
    """测试提示词引擎功能"""
    logger.info("\n=== 测试提示词引擎功能 ===")
    
    try:
        from core.prompt_engine import PromptEngine
        
        # 创建提示词引擎实例
        prompt_engine = PromptEngine()
        logger.info("提示词引擎实例创建成功")
        
        # 准备测试数据
        query = "贵州茅台2024年净利润增长率是多少？"
        history = []
        data_sources = {
            'knowledge_base': [
                {
                    'text_chunk': '贵州茅台2024年净利润为700亿元，同比增长15%',
                    'source': '贵州茅台2024年财报第5页'
                },
                {
                    'text_chunk': '公司实现营业收入1500亿元，同比增长12%',
                    'source': '贵州茅台2024年财报第4页'
                }
            ]
        }
        intent_analysis = {
            'primary_intent': 'general',
            'needs_knowledge_base': True
        }
        
        # 构建提示词
        prompt = prompt_engine.construct_prompt(
            query=query,
            history=history,
            data_sources=data_sources,
            intent_analysis=intent_analysis
        )
        
        logger.info(f"构建的提示词长度: {len(prompt)}")
        logger.info("提示词内容（前500字符）:")
        logger.info(prompt[:500] + "...")
        
        # 检查提示词是否包含来源信息
        if '来源：贵州茅台2024年财报第5页' in prompt:
            logger.info("✅ 提示词包含来源信息")
        else:
            logger.warning("❌ 提示词未包含来源信息")
        
        return True
        
    except Exception as e:
        logger.error(f"提示词引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_coordinator():
    """测试Agent协调器功能"""
    logger.info("\n=== 测试Agent协调器功能 ===")
    
    try:
        from core.agent_coordinator import FinancialAssistantAgent
        
        # 创建Agent实例
        agent = FinancialAssistantAgent()
        logger.info("Agent实例创建成功")
        
        # 准备测试数据
        user_id = "test_user_123"
        query = "贵州茅台2024年净利润增长率是多少？"
        
        logger.info(f"测试用户查询: {query}")
        
        # 处理查询（模拟模式）
        response = agent.process_query(user_id, query)
        
        logger.info(f"处理结果类型: {type(response)}")
        logger.info(f"处理结果: {response}")
        
        # 检查响应是否包含来源信息
        if response and 'response' in response:
            if '来源' in response['response']:
                logger.info("✅ 响应包含来源信息")
            else:
                logger.info("响应可能是模拟的，没有实际来源信息")
        
        return True
        
    except Exception as e:
        logger.error(f"Agent协调器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    logger.info("开始测试RAG功能...")
    
    # 运行所有测试
    tests = [
        test_knowledge_base,
        test_prompt_engine,
        test_agent_coordinator
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # 统计测试结果
    passed = sum(results)
    total = len(results)
    
    logger.info(f"\n=== 测试结果总结 ===")
    logger.info(f"通过测试数: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ 所有测试通过！")
        return 0
    else:
        logger.error(f"❌ 有 {total - passed} 个测试失败！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
