#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步下载所有沪深A股日k数据并保存为CSV格式
"""

import asyncio
import os
import sys
import logging
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_stock_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockDataDownloader:
    def __init__(self, output_dir: str = "stock_data"):
        """
        初始化股票数据下载器
        
        Args:
            output_dir: 数据保存目录
        """
        self.output_dir = output_dir
        self.total_stocks = 0
        self.success_count = 0
        self.fail_count = 0
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")
    
    def get_all_stock_list(self, max_retries: int = 3, retry_delay: int = 5) -> List[Tuple[str, str]]:
        """
        获取所有沪深A股股票列表，支持重试
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            
        Returns:
            List[Tuple[str, str]]: 股票代码和名称的列表，格式为[("600000.SS", "浦发银行"), ...]
        """
        logger.info("获取所有沪深A股股票列表...")
        
        # 真实获取股票列表
        for retry in range(max_retries):
            try:
                # 尝试使用ak.stock_zh_a_spot()获取股票列表
                try:
                    stock_list_df = ak.stock_zh_a_spot()
                    logger.info(f"成功获取 {len(stock_list_df)} 只股票列表")
                    
                    # 转换为[(code, name), ...]格式，添加交易所后缀
                    stock_list = []
                    for _, row in stock_list_df.iterrows():
                        code = str(row['代码'])
                        name = row['名称']
                        
                        # 检查股票代码是否已经包含交易所前缀或后缀
                        if code.startswith(('sh', 'sz')):
                            # 已经包含交易所前缀，转换为 .SS 或 .SZ 后缀格式
                            if code.startswith('sh'):
                                clean_code = code[2:]
                                full_code = clean_code + '.SS'
                            else:
                                clean_code = code[2:]
                                full_code = clean_code + '.SZ'
                        elif code.endswith(('.SS', '.SZ')):
                            # 已经包含交易所后缀，直接使用
                            full_code = code
                        else:
                            # 根据股票代码判断交易所，添加正确的后缀
                            # 000开头为深交所主板，300开头为创业板，002开头为中小板，都属于深交所(.SZ)
                            # 600开头为上交所(.SS)
                            suffix = ".SZ" if code.startswith(('000', '002', '300')) else ".SS"
                            full_code = code + suffix
                            
                        stock_list.append((full_code, name))
                    
                    return stock_list
                except Exception as e1:
                    logger.warning(f"使用ak.stock_zh_a_spot()获取股票列表失败: {e1}")
                    logger.info("尝试使用ak.stock_info_a_code_name()获取股票列表...")
                    
                    # 备选方案：使用ak.stock_info_a_code_name()获取股票列表
                    stock_list_df = ak.stock_info_a_code_name()
                    logger.info(f"成功获取 {len(stock_list_df)} 只股票列表")
                    
                    # 转换为[(code, name), ...]格式，添加交易所后缀
                    stock_list = []
                    for _, row in stock_list_df.iterrows():
                        code = str(row['code'])
                        name = row['name']
                        
                        # 检查股票代码是否已经包含交易所前缀或后缀
                        if code.startswith(('sh', 'sz')):
                            # 已经包含交易所前缀，转换为 .SS 或 .SZ 后缀格式
                            if code.startswith('sh'):
                                clean_code = code[2:]
                                full_code = clean_code + '.SS'
                            else:
                                clean_code = code[2:]
                                full_code = clean_code + '.SZ'
                        elif code.endswith(('.SS', '.SZ')):
                            # 已经包含交易所后缀，直接使用
                            full_code = code
                        else:
                            # 根据股票代码判断交易所，添加正确的后缀
                            # 000开头为深交所主板，300开头为创业板，002开头为中小板，都属于深交所(.SZ)
                            # 600开头为上交所(.SS)
                            suffix = ".SZ" if code.startswith(('000', '002', '300')) else ".SS"
                            full_code = code + suffix
                            
                        stock_list.append((full_code, name))
                    
                    return stock_list
            except Exception as e:
                logger.error(f"获取股票列表失败(第{retry+1}/{max_retries}次): {e}")
                if retry < max_retries - 1:
                    logger.info(f"{retry_delay}秒后重试...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.error("已达到最大重试次数，获取股票列表失败")
                    raise
        
        return []
    
    async def download_single_stock_data(self, stock: Tuple[str, str], start_date: str, end_date: str, max_retries: int = 3, retry_delay: int = 3) -> bool:
        """
        异步下载单只股票的日k数据，支持重试
        
        Args:
            stock: (股票代码, 股票名称)
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            
        Returns:
            bool: 下载是否成功
        """
        stock_code, stock_name = stock
        logger.info(f"开始下载 {stock_name}({stock_code}) 的日k数据...")
        
        for retry in range(max_retries):
            try:
                # 提取纯数字代码
                numeric_code = stock_code.replace('.SS', '').replace('.SZ', '')
                
                # 从2000年开始逐年尝试下载数据，直到找到有数据的年份
                logger.info(f"开始从2000年逐年尝试下载 {stock_name}({stock_code}) 的数据...")
                import datetime
                current_year = datetime.datetime.now().year
                found_data = False
                first_year = 2000
                
                # 逐年下载并合并数据
                all_data = []
                
                for year in range(2000, current_year + 1):
                    year_start = f"{year}0101"
                    year_end = f"{year}1231"
                    
                    try:
                        logger.info(f"尝试下载 {stock_name}({stock_code}) {year}年的数据...")
                        year_df = await asyncio.to_thread(
                            ak.stock_zh_a_hist,
                            symbol=numeric_code,
                            period="daily",
                            start_date=year_start,
                            end_date=year_end,
                            adjust="qfq"  # 前复权
                        )
                        
                        if not year_df.empty:
                            found_data = True
                            logger.info(f"找到 {stock_name}({stock_code}) {year}年的数据，共 {len(year_df)} 条记录")
                            all_data.append(year_df)
                        else:
                            logger.info(f"{stock_name}({stock_code}) {year}年没有数据")
                    except Exception as e:
                        logger.warning(f"下载 {stock_name}({stock_code}) {year}年数据失败: {e}")
                        # 继续尝试下一年的数据
                
                if found_data and all_data:
                    # 合并所有年份的数据
                    df = pd.concat(all_data, ignore_index=True)
                    logger.info(f"{stock_name}({stock_code}) 共下载到 {len(df)} 条记录")
                    
                    # 确保数据按日期排序
                    df = df.sort_values('日期')
                else:
                    logger.warning(f"{stock_name}({stock_code}) 从2000年到现在都没有数据")
                    self.fail_count += 1
                    return False
                
                # 转换数据格式为与现有缓存兼容的JSON格式
                # 移除交易所后缀，只保留数字代码
                clean_code = stock_code.replace('.SS', '').replace('.SZ', '')
                # 使用最早的开始日期和最晚的结束日期
                json_data = {
                    "symbol": stock_code,
                    "interval": "1d",
                    "start_date": "20000101",  # 固定从2000年开始
                    "end_date": f"{current_year}1231",  # 到当前年份结束
                    "data": []
                }
                
                # 添加数据到JSON
                for _, row in df.iterrows():
                    # 确保日期转换为字符串
                    date_str = row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期'])
                    json_data["data"].append({
                        "日期": date_str,
                        "股票代码": row['股票代码'],
                        "开盘": row['开盘'],
                        "收盘": row['收盘'],
                        "最高": row['最高'],
                        "最低": row['最低'],
                        "成交量": row['成交量'],
                        "成交额": row['成交额'],
                        "振幅": row['振幅'],
                        "涨跌幅": row['涨跌幅'],
                        "涨跌额": row['涨跌额'],
                        "换手率": row['换手率']
                    })
                
                # 保存为JSON文件到cache/stock_data目录
                import json
                cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache", "stock_data")
                os.makedirs(cache_dir, exist_ok=True)
                
                filename = f"{stock_code}_1d.json"
                filepath = os.path.join(cache_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"成功下载 {stock_name}({stock_code}) 的日k数据，共 {len(df)} 条记录")
                self.success_count += 1
                return True
                
            except Exception as e:
                logger.error(f"下载 {stock_name}({stock_code}) 失败(第{retry+1}/{max_retries}次): {e}")
                import traceback
                logger.error(f"详细错误信息: {traceback.format_exc()}")
                if retry < max_retries - 1:
                    logger.info(f"{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"下载 {stock_name}({stock_code}) 失败，已达到最大重试次数")
                    self.fail_count += 1
                    return False
    
    async def download_all_stocks_data(self, start_date: str, end_date: str, stock_list: List[Tuple[str, str]], max_concurrency: int = 10) -> None:
        """
        并发下载所有股票的日k数据
        
        Args:
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            stock_list: 股票列表，格式为[(code, name), ...]
            max_concurrency: 最大并发数
        """
        
        self.total_stocks = len(stock_list)
        logger.info(f"开始下载 {self.total_stocks} 只股票的日k数据，时间范围: {start_date} 到 {end_date}")
        logger.info(f"最大并发数: {max_concurrency}")
        
        # 创建任务队列
        tasks = []
        
        # 使用Semaphore控制并发
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def bounded_download(stock):
            async with semaphore:
                await self.download_single_stock_data(stock, start_date, end_date, max_retries=3, retry_delay=3)
        
        # 创建所有任务
        for stock in stock_list:
            tasks.append(bounded_download(stock))
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 输出统计信息
        logger.info("\n" + "="*60)
        logger.info("股票数据下载完成")
        logger.info(f"总股票数: {self.total_stocks}")
        logger.info(f"成功下载: {self.success_count}")
        logger.info(f"下载失败: {self.fail_count}")
        logger.info("="*60)
    
    def run(self, start_date: str, end_date: str, max_concurrency: int = 10, limit: int = None, test_stocks: bool = False, test_stock: str = None) -> None:
        """
        运行下载任务
        
        Args:
            start_date: 开始日期，格式YYYY-MM-DD
            end_date: 结束日期，格式YYYY-MM-DD
            max_concurrency: 最大并发数
            limit: 限制下载的股票数量，None表示下载所有股票
            test_stocks: 是否使用测试股票列表（知名股票）
            test_stock: 测试模式，指定单个股票代码（格式：600519.SS）
        """
        # 测试模式：指定单个股票
        if test_stock:
            logger.info(f"测试模式：只下载 {test_stock} 一只股票")
            # 获取股票名称
            try:
                stock_name = "测试股票"
                # 尝试获取真实股票名称
                if test_stock.endswith('.SS') or test_stock.endswith('.SZ'):
                    numeric_code = test_stock[:-3]
                else:
                    numeric_code = test_stock
                
                # 尝试使用akshare获取股票名称
                try:
                    stock_list_df = ak.stock_zh_a_spot()
                    stock_data = stock_list_df[stock_list_df['代码'] == numeric_code]
                    if not stock_data.empty:
                        stock_name = stock_data.iloc[0]['名称']
                except Exception:
                    # 如果失败，使用备选方法
                    try:
                        stock_list_df = ak.stock_info_a_code_name()
                        stock_data = stock_list_df[stock_list_df['code'] == numeric_code]
                        if not stock_data.empty:
                            stock_name = stock_data.iloc[0]['name']
                    except Exception:
                        pass
                
                stock_list = [(test_stock, stock_name)]
            except Exception as e:
                logger.warning(f"获取测试股票名称失败: {e}")
                stock_list = [(test_stock, "未知股票")]
        else:
            # 获取所有股票列表
            stock_list = self.get_all_stock_list()
            
            # 测试模式：只下载一些知名股票
            if test_stocks and limit is None:
                predefined_test_stocks = [
                    ("600519.SS", "贵州茅台"),
                    ("601398.SS", "工商银行"),
                    ("600036.SS", "招商银行"),
                    ("000002.SZ", "万科A"),
                    ("000858.SZ", "五粮液")
                ]
                # 过滤出存在的测试股票
                stock_list = [stock for stock in stock_list if stock in predefined_test_stocks]
            elif limit is not None and limit > 0:
                stock_list = stock_list[:limit]
        
        # 开始下载
        asyncio.run(self.download_all_stocks_data(start_date, end_date, stock_list, max_concurrency))


def main():
    """
    主函数
    """
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='异步下载所有沪深A股日k数据')
    parser.add_argument('--start-date', type=str, default='2000-01-01',
                        help='开始日期，格式YYYY-MM-DD，默认2000-01-01（尽可能早的日期）')
    parser.add_argument('--end-date', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                        help='结束日期，格式YYYY-MM-DD，默认今天')
    parser.add_argument('--output-dir', type=str, default='stock_data',
                        help='数据保存目录，默认stock_data')
    parser.add_argument('--max-concurrency', type=int, default=10,
                        help='最大并发数，默认10')
    parser.add_argument('--limit', type=int, default=None,
                        help='限制下载的股票数量，默认下载所有股票')
    parser.add_argument('--test-stocks', action='store_true',
                        help='只下载一些知名测试股票（贵州茅台、工商银行等）')
    parser.add_argument('--test-stock', type=str, default=None,
                        help='测试模式：指定单个股票代码（格式：600519.SS）')
    
    args = parser.parse_args()
    
    try:
        # 创建下载器实例
        downloader = StockDataDownloader(args.output_dir)
        
        # 运行下载任务
        downloader.run(args.start_date, args.end_date, args.max_concurrency, args.limit, args.test_stocks, args.test_stock)
        
        logger.info("所有任务完成！")
        return 0
    except KeyboardInterrupt:
        logger.info("用户中断下载")
        return 1
    except Exception as e:
        logger.error(f"程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())