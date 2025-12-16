#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从API拉取所有沪深A股股票名称和代码的映射，并保存为CSV文件
"""

import pandas as pd
import akshare as ak
import os
import logging
from typing import Dict

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('generate_stock_mapping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_stock_mapping() -> Dict[str, str]:
    """
    生成股票名称到代码的映射
    
    Returns:
        Dict[str, str]: 股票名称到代码的映射字典
    """
    logger.info("开始从API拉取所有沪深A股股票列表...")
    
    try:
        # 使用akshare获取所有A股股票列表
        stock_list_df = ak.stock_zh_a_spot()
        logger.info(f"成功获取 {len(stock_list_df)} 只股票列表")
        
        # 转换为股票名称到代码的映射字典
        stock_mapping = {}
        for _, row in stock_list_df.iterrows():
            code = str(row['代码'])
            name = row['名称']
            # 根据股票代码判断交易所
            # 000开头为深交所主板，300开头为创业板，002开头为中小板，都属于深交所(.SZ)
            # 600开头为上交所(.SS)
            suffix = ".SZ" if code.startswith(('000', '002', '300')) else ".SS"
            full_code = code + suffix
            stock_mapping[name] = full_code
        
        return stock_mapping
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        logger.info("使用本地备份的股票列表...")
        # 如果API调用失败，使用简单的备份列表
        return {
            "贵州茅台": "600519.SS",
            "宁德时代": "300750.SZ",
            "招商银行": "600036.SS",
            "比亚迪": "002594.SZ",
            "平安银行": "000001.SZ",
            "兴业银行": "601166.SS",
            "中国平安": "601318.SS",
            "工商银行": "601398.SS",
            "建设银行": "601939.SS",
            "中国石油": "601857.SS",
            "上海电力": "600021.SS",
            "神州信息": "000555.SZ",
            "阿里巴巴": "BABA.US",
            "腾讯控股": "00700.HK",
            "百度": "BIDU.US",
            "京东": "JD.US",
            "美团": "03690.HK",
            "拼多多": "PDD.US",
            "小米集团": "01810.HK",
            "网易": "NTES.US",
            "新浪": "SINA.US",
            "搜狐": "SOHU.US"
        }


def save_stock_mapping_to_csv(stock_mapping: Dict[str, str], file_path: str) -> None:
    """
    将股票映射保存为CSV文件
    
    Args:
        stock_mapping: 股票名称到代码的映射字典
        file_path: CSV文件路径
    """
    # 创建数据帧
    df = pd.DataFrame(list(stock_mapping.items()), columns=['股票名称', '股票代码'])
    
    # 保存为CSV文件
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    logger.info(f"股票映射已保存到CSV文件: {file_path}")
    logger.info(f"共包含 {len(df)} 条股票映射记录")


def load_stock_mapping_from_csv(file_path: str) -> Dict[str, str]:
    """
    从CSV文件加载股票映射
    
    Args:
        file_path: CSV文件路径
    
    Returns:
        Dict[str, str]: 股票名称到代码的映射字典
    """
    if not os.path.exists(file_path):
        logger.error(f"股票映射CSV文件不存在: {file_path}")
        return {}
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        stock_mapping = dict(zip(df['股票名称'], df['股票代码']))
        logger.info(f"从CSV文件加载了 {len(stock_mapping)} 条股票映射记录")
        return stock_mapping
    except Exception as e:
        logger.error(f"加载股票映射CSV文件失败: {e}")
        return {}


if __name__ == "__main__":
    print("=== 生成股票映射CSV文件 ===")
    
    # 定义CSV文件路径
    csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "stock_mapping.csv")
    
    # 确保data目录存在
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
    
    # 生成股票映射
    stock_mapping = generate_stock_mapping()
    
    # 保存到CSV文件
    save_stock_mapping_to_csv(stock_mapping, csv_file_path)
    
    # 验证加载
    loaded_mapping = load_stock_mapping_from_csv(csv_file_path)
    
    print(f"生成的股票映射条数: {len(stock_mapping)}")
    print(f"加载的股票映射条数: {len(loaded_mapping)}")
    print(f"股票映射CSV文件路径: {csv_file_path}")
    
    # 显示前10条记录
    print("\n前10条股票映射记录:")
    for i, (name, code) in enumerate(list(loaded_mapping.items())[:10]):
        print(f"{i+1}. {name} -> {code}")
    
    print("\n股票映射CSV文件生成完成！")
