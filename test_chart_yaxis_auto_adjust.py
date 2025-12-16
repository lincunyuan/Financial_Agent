#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试图表Y轴自动范围调整功能
"""

import pandas as pd
import numpy as np
from core.chart_generator import ChartGenerator
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_test_data(start_date, end_date, base_price=10, volatility=0.1):
    """
    生成测试股票数据
    
    参数:
        start_date: 开始日期
        end_date: 结束日期
        base_price: 基础价格
        volatility: 波动率
    
    返回:
        包含日期、开盘、收盘、最高、最低、成交量的DataFrame
    """
    # 生成日期范围
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 只生成工作日
    
    # 生成价格数据
    np.random.seed(42)  # 固定随机种子以确保可重复性
    price_changes = np.random.normal(0, volatility, len(dates))
    
    # 计算价格 - 使用Pandas Series
    close = pd.Series(base_price * (1 + price_changes).cumprod(), index=dates)
    open = close.shift(1).fillna(base_price)  # 前一天的收盘价作为今天的开盘价
    high = close + np.abs(pd.Series(np.random.normal(0, volatility/2, len(dates)), index=dates))
    low = close - np.abs(pd.Series(np.random.normal(0, volatility/2, len(dates)), index=dates))
    
    # 生成成交量
    volume = np.random.randint(1000000, 10000000, len(dates))
    
    # 创建DataFrame
    data = pd.DataFrame({
        '日期': dates,
        '开盘': open.values,
        '收盘': close.values,
        '最高': high.values,
        '最低': low.values,
        '成交量': volume
    })
    
    return data

def test_yaxis_auto_adjust():
    """
    测试Y轴自动范围调整功能
    """
    logger.info("开始测试Y轴自动范围调整功能...")
    
    # 生成测试数据
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)
    test_data = generate_test_data(start_date, end_date, base_price=10, volatility=0.02)
    
    logger.info(f"生成测试数据: {len(test_data)} 条记录")
    logger.info(f"价格范围: {test_data['最低'].min():.2f} - {test_data['最高'].max():.2f}")
    
    # 创建图表生成器
    chart_generator = ChartGenerator(output_dir="test_charts")
    
    # 测试K线图
    logger.info("测试K线图生成...")
    kline_fig = chart_generator.generate_k_line_chart("TEST.XX", test_data, title="测试K线图")
    if kline_fig:
        logger.info("K线图生成成功")
        # 保存图表
        chart_generator.save_chart(kline_fig, "test_kline_chart", file_format="html")
        logger.info("K线图已保存为HTML文件")
    else:
        logger.error("K线图生成失败")
    
    # 测试折线图
    logger.info("测试折线图生成...")
    line_fig = chart_generator.generate_line_chart("TEST.XX", test_data, title="测试折线图")
    if line_fig:
        logger.info("折线图生成成功")
        # 保存图表
        chart_generator.save_chart(line_fig, "test_line_chart", file_format="html")
        logger.info("折线图已保存为HTML文件")
    else:
        logger.error("折线图生成失败")
    
    # 测试成交量图
    logger.info("测试成交量图生成...")
    volume_fig = chart_generator.generate_volume_chart("TEST.XX", test_data, title="测试成交量图")
    if volume_fig:
        logger.info("成交量图生成成功")
        # 保存图表
        chart_generator.save_chart(volume_fig, "test_volume_chart", file_format="html")
        logger.info("成交量图已保存为HTML文件")
    else:
        logger.error("成交量图生成失败")
    
    logger.info("测试完成！请在浏览器中打开生成的HTML文件测试Y轴自动调整功能。")
    logger.info("测试方法：")
    logger.info("1. 打开生成的HTML图表文件")
    logger.info("2. 使用X轴的范围滑块调整显示范围")
    logger.info("3. 观察Y轴范围是否会自动调整以适应当前X轴范围内的数据")
    logger.info("4. 手动拖动Y轴查看是否可以调整")

if __name__ == "__main__":
    test_yaxis_auto_adjust()