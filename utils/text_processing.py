# 文本处理工具模块
import re
from datetime import datetime

def insert_current_time(text):
    """
    检测文本中的时间相关查询并插入当前时间
    
    Args:
        text: 需要处理的文本
        
    Returns:
        处理后的文本
    """
    # 获取当前时间
    now = datetime.now()
    current_date = now.strftime("%Y年%m月%d日")
    current_time = now.strftime("%H:%M:%S")
    current_datetime = now.strftime("%Y年%m月%d日 %H:%M:%S")
    weekday = get_weekday(now.weekday())
    
    # 定义时间查询问题和对应的回答
    time_queries = {
        "今天是什么时间": f"今天的时间是{current_datetime}。",
        "今天是什么时间？": f"今天的时间是{current_datetime}。",
        "今天是什么日期": f"今天的日期是{current_date}。",
        "今天是什么日期？": f"今天的日期是{current_date}。",
        "现在的时间是多少": f"现在的时间是{current_time}。",
        "现在的时间是多少？": f"现在的时间是{current_time}。",
        "当前时间": f"当前时间是{current_time}。",
        "当前时间？": f"当前时间是{current_time}。",
        "现在几点": f"现在的时间是{current_time}。",
        "现在几点？": f"现在的时间是{current_time}。",
        "今天是几号": f"今天是{current_date}。",
        "今天是几号？": f"今天是{current_date}。",
        "今天是星期几": f"今天是{weekday}。",
        "今天是星期几？": f"今天是{weekday}。",
        "今天周几": f"今天是{weekday}。",
        "今天周几？": f"今天是{weekday}。",
        "今天是什么日子": f"今天是{current_date}。",
        "今天是什么日子？": f"今天是{current_date}。",
    }
    
    # 首先检查是否是完整的时间查询问题
    text_stripped = text.strip()
    if text_stripped in time_queries:
        return time_queries[text_stripped]
    
    # 然后处理包含"今天"的短语替换
    processed_text = text
    processed_text = re.sub(r'今天的(?=股票|行情|财经|新闻|数据)', f'{current_date}的', processed_text)
    processed_text = re.sub(r'今天 (?=股票|行情|财经|新闻|数据)', f'{current_date} ', processed_text)
    
    return processed_text

def format_prompt_with_context(query, history_or_context=[], chunks=[], tool_data={}):
    """
    格式化带有上下文的提示词
    
    Args:
        query: 用户的问题
        history_or_context: 历史对话记录（新调用方式）或上下文字符串（旧调用方式）
        chunks: 知识库检索的相关内容
        tool_data: 工具获取的相关数据
        
    Returns:
        格式化后的提示词
    """
    # 处理实时时间查询
    processed_query = insert_current_time(query)
    
    # 构建上下文信息
    context_parts = []
    
    # 判断第二个参数是历史对话列表还是上下文字符串
    if history_or_context:
        if isinstance(history_or_context, str):
            # 旧的调用方式：第二个参数是上下文字符串
            context_parts.append(f"上下文信息：{history_or_context}")
        else:
            # 新的调用方式：第二个参数是历史对话列表
            history_str = "\n".join([f"用户: {h[0]}\n助手: {h[1]}" for h in history_or_context])
            context_parts.append(f"历史对话：\n{history_str}")
    
    # 添加知识库检索内容
    if chunks:
        chunks_str = "\n".join([f"[{i+1}] {chunk['content'][:200]}..." for i, chunk in enumerate(chunks[:3])])  # 只取前3个结果
        context_parts.append(f"相关知识库内容：\n{chunks_str}")
    
    # 添加工具数据
    if tool_data:
        tool_str = "\n".join([f"{k}: {v}" for k, v in tool_data.items()])
        context_parts.append(f"实时工具数据：\n{tool_str}")
    
    if context_parts:
        context = "\n\n".join(context_parts)
        prompt = f"{context}\n\n用户问题：{processed_query}\n\n请根据提供的信息回答用户问题。"
    else:
        prompt = f"用户问题：{processed_query}\n\n请直接回答用户问题。"
    
    return prompt

def get_weekday(weekday_num):
    """
    将星期数字转换为中文
    
    Args:
        weekday_num: 星期数字（0-6，0表示周一）
        
    Returns:
        中文星期
    """
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[weekday_num]

def extract_keywords(text):
    """
    从文本中提取关键词
    
    Args:
        text: 需要提取关键词的文本
        
    Returns:
        关键词列表
    """
    # 简单的关键词提取，可根据需要扩展
    # 移除特殊字符
    text = re.sub(r'[^\w\u4e00-\u9fa5]', ' ', text)
    # 分割为单词
    words = text.split()
    # 过滤掉短词和常见停用词
    stop_words = set(["的", "了", "和", "是", "在", "我", "有", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"])
    keywords = [word for word in words if len(word) > 1 and word not in stop_words]
    
    return keywords

def clean_text(text):
    """
    清理文本，去除多余空格和特殊字符
    
    Args:
        text: 需要清理的文本
        
    Returns:
        清理后的文本
    """
    # 去除首尾空格
    text = text.strip()
    # 替换多个空格为一个
    text = re.sub(r'\s+', ' ', text)
    # 去除特殊字符（保留中文、英文、数字、常用标点）
    text = re.sub(r'[^\w\u4e00-\u9fa5，。！？；：、,.!?;:]', '', text)
    
    return text