#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从下载的股票数据生成图表
"""

import sys
import json
import os
import pandas as pd
import logging
from datetime import datetime

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.chart_generator import ChartGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'generate_charts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_stock_data(file_path: str) -> dict:
    """加载股票数据
    
    参数:
        file_path: 数据文件路径
        
    Returns:
        股票数据字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"成功加载数据: {file_path}")
        return data
    except Exception as e:
        logger.error(f"加载数据失败: {file_path}, 错误: {e}")
        return None

def convert_to_dataframe(stock_data: dict) -> pd.DataFrame:
    """将股票数据转换为DataFrame
    
    参数:
        stock_data: 股票数据字典
        
    Returns:
        包含股票数据的DataFrame
    """
    try:
        if 'data' not in stock_data:
            logger.error("数据中没有'data'字段")
            return None
        
        df = pd.DataFrame(stock_data['data'])
        
        # 打印前几行数据，查看实际的键名
        logger.info(f"数据前几行: {df.head()}")
        logger.info(f"数据列名: {df.columns.tolist()}")
        
        # 中文乱码键名到正确中文键名的映射
        # 注意：键名末尾的问号可能是显示问题，实际键名可能没有问号
        column_mapping = {
            '鏃ユ湡': '日期',
            '鑲＄エ浠ｇ爜': '股票代码',
            '寮€鐩?': '开盘',
            '寮€鐩': '开盘',  # 备选键名，不带问号
            '鏀剁洏': '收盘',
            '鏈€楂?': '最高',
            '鏈€楂': '最高',  # 备选键名，不带问号
            '鏈€浣?': '最低',
            '鏈€浣': '最低',  # 备选键名，不带问号
            '鎴愪氦閲?': '成交量',
            '鎴愪氦閲': '成交量',  # 备选键名，不带问号
            '鎴愪氦棰?': '成交额',
            '鎴愪氦棰': '成交额',  # 备选键名，不带问号
            '鎸箙': '振幅',
            '娑ㄨ穼骞?': '涨跌幅',
            '娑ㄨ穼骞': '涨跌幅',  # 备选键名，不带问号
            '娑ㄨ穼棰?': '涨跌额',
            '娑ㄨ穼棰': '涨跌额',  # 备选键名，不带问号
            '鎹㈡墜鐜?': '换手率',
            '鎹㈡墜鐜': '换手率'  # 备选键名，不带问号
        }
        
        # 只保留数据中实际存在的键名的映射
        actual_columns = df.columns.tolist()
        valid_mapping = {k: v for k, v in column_mapping.items() if k in actual_columns}
        
        logger.info(f"有效的键名映射: {valid_mapping}")
        
        # 重命名列
        df = df.rename(columns=valid_mapping)
        
        logger.info(f"成功转换为DataFrame，共 {len(df)} 条记录")
        logger.info(f"转换后的列名: {df.columns.tolist()}")
        return df
    except Exception as e:
        logger.error(f"转换DataFrame失败: {e}")
        return None

def process_all_stocks(stock_data_dir: str, charts_dir: str) -> None:
    """处理所有股票数据并生成图表
    
    参数:
        stock_data_dir: 股票数据目录
        charts_dir: 图表保存目录
    """
    try:
        # 创建图表生成器
        chart_generator = ChartGenerator(output_dir=charts_dir)
        
        # 获取所有JSON文件
        json_files = [f for f in os.listdir(stock_data_dir) if f.endswith('.json')]
        total_files = len(json_files)
        logger.info(f"找到 {total_files} 个股票数据文件")
        
        # 处理每个文件
        processed_count = 0
        for json_file in json_files:
            file_path = os.path.join(stock_data_dir, json_file)
            stock_code = os.path.splitext(json_file)[0].replace('_1d', '')
            
            logger.info(f"处理第 {processed_count+1}/{total_files} 个文件: {json_file}")
            
            # 加载数据
            stock_data = load_stock_data(file_path)
            if not stock_data:
                continue
            
            # 转换为DataFrame
            df = convert_to_dataframe(stock_data)
            if df is None or df.empty:
                logger.warning(f"{stock_code} 没有有效数据")
                continue
            
            # 生成并保存所有图表
            try:
                saved_charts = chart_generator.generate_and_save_all_charts(stock_code, df)
                logger.info(f"{stock_code} 图表生成完成: {saved_charts}")
                processed_count += 1
            except Exception as e:
                logger.error(f"{stock_code} 图表生成失败: {e}")
                continue
        
        logger.info(f"所有处理完成，共处理 {processed_count}/{total_files} 个股票文件")
        
    except Exception as e:
        logger.error(f"处理所有股票失败: {e}", exc_info=True)
        raise

def main():
    """主函数"""
    try:
        import argparse
        
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='从下载的股票数据生成图表')
        parser.add_argument('--stock-code', type=str, help='指定要处理的股票代码，如600519.SS，不指定则处理所有')
        parser.add_argument('--stock-data-dir', type=str, default='d:\\code\\financial_assistant_agent\\cache\\stock_data', help='股票数据目录')
        parser.add_argument('--charts-dir', type=str, default='d:\\code\\financial_assistant_agent\\charts', help='图表保存目录')
        args = parser.parse_args()
        
        # 确保目录存在
        os.makedirs(args.charts_dir, exist_ok=True)
        
        logger.info("开始从下载数据生成图表")
        logger.info(f"股票数据目录: {args.stock_data_dir}")
        logger.info(f"图表保存目录: {args.charts_dir}")
        
        if args.stock_code:
            # 只处理指定的股票
            logger.info(f"只处理股票: {args.stock_code}")
            process_single_stock(args.stock_code, args.stock_data_dir, args.charts_dir)
        else:
            # 处理所有股票
            process_all_stocks(args.stock_data_dir, args.charts_dir)
        
        logger.info("图表生成完成")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        raise

def process_single_stock(stock_code: str, stock_data_dir: str, charts_dir: str) -> None:
    """处理单个股票数据并生成图表
    
    参数:
        stock_code: 股票代码
        stock_data_dir: 股票数据目录
        charts_dir: 图表保存目录
    """
    try:
        # 创建图表生成器
        chart_generator = ChartGenerator(output_dir=charts_dir)
        
        # 标准化股票代码格式
        processed_code = stock_code
        
        # 移除可能的sh/sz前缀
        if processed_code.startswith('sh'):
            processed_code = processed_code[2:]
        elif processed_code.startswith('sz'):
            processed_code = processed_code[2:]
        
        # 确保有交易所后缀
        if '.' not in processed_code:
            # 根据代码判断交易所
            if processed_code.startswith(('600', '601', '603', '605')):
                processed_code += '.SS'  # 上交所
            else:
                processed_code += '.SZ'  # 深交所
        
        # 构建可能的文件路径列表
        possible_files = [
            os.path.join(stock_data_dir, f"{processed_code}_1d.json"),
            os.path.join(stock_data_dir, f"sh{processed_code}_1d.json"),
            os.path.join(stock_data_dir, f"sz{processed_code}_1d.json")
        ]
        
        # 查找存在的文件，优先选择最大的文件（通常包含完整数据）
        file_path = None
        max_size = 0
        
        for file in possible_files:
            if os.path.exists(file):
                file_size = os.path.getsize(file)
                if file_size > max_size:
                    max_size = file_size
                    file_path = file
        
        if not file_path:
            # 如果没有找到，尝试直接使用原始代码
            original_file = os.path.join(stock_data_dir, f"{stock_code}_1d.json")
            if os.path.exists(original_file):
                file_path = original_file
            else:
                logger.error(f"找不到股票数据文件: {stock_code}")
                logger.info(f"尝试的文件路径: {possible_files}")
                logger.info(f"缓存目录文件列表: {os.listdir(stock_data_dir)[:10]}...")  # 显示前10个文件
                return
        
        logger.info(f"使用数据文件: {file_path} (大小: {max_size} 字节)")
        
        # 加载数据
        stock_data = load_stock_data(file_path)
        if not stock_data:
            return
        
        # 转换为DataFrame
        df = convert_to_dataframe(stock_data)
        if df is None or df.empty:
            logger.warning(f"{stock_code} 没有有效数据")
            return
        
        # 生成并保存所有图表
        saved_charts = chart_generator.generate_and_save_all_charts(processed_code, df)
        logger.info(f"{stock_code} 图表生成完成: {saved_charts}")
        
    except Exception as e:
        logger.error(f"处理单个股票失败: {stock_code}, 错误: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()