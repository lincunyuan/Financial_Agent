# 测试ETF实体识别功能
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.intent_recognizer import IntentRecognizer

# 初始化意图识别器
recognizer = IntentRecognizer()

# 测试ETF识别功能
test_queries = [
    "黄金ETF",  # 大写ETF
    "黄金etf",  # 小写etf
    "黄金Etf",  # 混合大小写
    "白银ETF",
    "石油ETF",
    "新能源ETF"
]

print("=== ETF实体识别测试 ===")
for query in test_queries:
    print(f"\n测试查询: {query}")
    analysis = recognizer.analyze(query)
    print(f"识别意图: {analysis['primary_intent']}")
    print(f"置信度: {analysis['confidence']:.2f}")
    print(f"提取实体: {analysis['entities']}")
    if analysis['entities']:
        for entity in analysis['entities']:
            # 适应不同的实体格式
            entity_type = entity.get('type', 'unknown')
            entity_name = entity.get('name', entity.get('value', 'unknown'))
            entity_value = entity.get('value', 'unknown')
            print(f"  - 实体类型: {entity_type}, 名称: {entity_name}, 代码: {entity_value}")
