import json
import os

# 使用原始字符串或正确的转义
file_path = r'D:\code\financial_assistant_agent\cache\stock_data\sh600021.SS_1d.json'

print(f"正在检查缓存文件: {file_path}")
print(f"文件存在: {os.path.exists(file_path)}")

if os.path.exists(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✅ JSON格式有效")
        print(f"数据类型: {type(data)}")
        print(f"包含的键: {list(data.keys())}")
        
        if isinstance(data, dict) and 'data' in data:
            print(f"data数组长度: {len(data['data'])}")
            
            if data['data']:
                print(f"\n第一条记录:")
                first_record = data['data'][0]
                print(f"  记录类型: {type(first_record)}")
                print(f"  键名: {list(first_record.keys())}")
                print(f"  完整记录: {first_record}")
    except Exception as e:
        print(f"❌ JSON解析失败: {e}")
