#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Selenium模拟人类点击方式从上海证券交易所下载财报
"""

import os
import time
import logging
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sse_financial_report_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SSEFinancialReportDownloader:
    """
    上交所财报下载器，使用Selenium模拟浏览器操作
    """
    def __init__(self, download_dir: str = "data/pdfs/sse", headless: bool = False):
        """
        初始化下载器
        
        Args:
            download_dir: 下载目录
            headless: 是否使用无头模式
        """
        self.download_dir = download_dir
        self.headless = headless
        
        # 创建下载目录
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"创建下载目录: {download_dir}")
        
        # 配置Chrome浏览器
        self.options = Options()
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 设置下载目录
        self.options.add_experimental_option('prefs', {
            'download.default_directory': os.path.abspath(download_dir),
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False,
            'plugins.always_open_pdf_externally': True
        })
        
        if headless:
            self.options.add_argument('--headless')
        
        # 初始化浏览器
        self.driver = None
        self.service = None
    
    def __enter__(self):
        """进入上下文管理器"""
        # 使用用户提供的Chrome浏览器和驱动路径
        chrome_path = "D:\\code\\chorme\\chrome-win64\\chrome.exe"
        chromedriver_path = "D:\\code\\chorme\\chromedriver-win64\\chromedriver.exe"
        
        self.options.binary_location = chrome_path
        self.service = Service(chromedriver_path)
        
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        logger.info("Chrome浏览器已启动")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if self.driver:
            self.driver.quit()
            logger.info("浏览器已关闭")
        if self.service:
            self.service.stop()
            logger.info("Chrome驱动服务已停止")
    
    def open_announcement_page(self):
        """
        打开上交所公告页面
        """
        url = "https://www.sse.com.cn/disclosure/listedinfo/announcement/"
        logger.info(f"访问上交所公告页面: {url}")
        self.driver.get(url)
        
        # 等待页面加载
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            logger.info("页面加载完成")
        except Exception as e:
            logger.error(f"页面加载失败: {e}")
            raise
    
    def select_report_type(self, report_type: str = None):
        """
        选择报告类型
        
        Args:
            report_type: 报告类型，可选值：'年报', '一季报', '三季报', '半年报'。如果为None则不限制类型。
        """
        if not report_type:
            logger.info("不限制报告类型")
            return
            
        logger.info(f"选择报告类型: {report_type}")
        
        try:
            # 查找报告类型选择区域（不滚动页面，依赖search_stock后的统一滚动）
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "announceTypeList"))
            )
            
            # 查找定期报告大类
            regular_report_div = self.driver.find_element(By.XPATH, "//div[contains(@class, 'announceDiv') and contains(.//b[@class='btype-name'], '定期报告')]")
            logger.info("找到定期报告大类")
            
            # 确保定期报告子列表已展开
            # 无论是否包含announce-child类，都尝试点击展开
            regular_report_div.click()
            logger.info("尝试展开定期报告子列表")
            time.sleep(3)  # 增加等待时间，确保子列表完全展开
            
            # 查找具体的报告类型选项
            report_type_items = regular_report_div.find_elements(By.XPATH, ".//ul[@class='small-type-list']/li")
            logger.info(f"找到 {len(report_type_items)} 个定期报告子选项")
            
            # 打印所有找到的报告类型选项，便于调试
            all_report_types = []
            for item in report_type_items:
                item_text = item.text.strip()
                all_report_types.append(item_text)
                logger.debug(f"定期报告子选项: {item_text}")
            logger.info(f"所有报告类型选项: {', '.join(all_report_types)}")
            
            selected = False
            for item in report_type_items:
                item_text = item.text.strip()
                
                # 只处理指定的报告类型，忽略其他所有类型
                if report_type == item_text:
                    logger.info(f"正在选择目标报告类型: {report_type}")
                    # 点击选择该报告类型（点击圆框图标）
                    try:
                        icon = item.find_element(By.CLASS_NAME, "iconcircle")
                        icon.click()
                        logger.info(f"已成功选择报告类型: {report_type}")
                        selected = True
                        break
                    except Exception as inner_e:
                        logger.error(f"点击报告类型图标失败: {inner_e}")
                        # 尝试直接点击整个选项
                        logger.info(f"尝试直接点击报告类型选项: {report_type}")
                        item.click()
                        logger.info(f"已直接点击选择报告类型: {report_type}")
                        selected = True
                        break
                else:
                    # 明确忽略所有非目标报告类型
                    logger.info(f"忽略非目标报告类型: {item_text}")
            
            if not selected:
                logger.error(f"未找到报告类型: {report_type}")
                raise ValueError(f"未找到报告类型: {report_type}")
                
        except Exception as e:
            logger.error(f"选择报告类型失败: {e}")
            # 保存当前页面以分析问题
            with open('report_type_selection_error.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("页面内容已保存到 report_type_selection_error.html")
            raise
    
    def search_stock(self, stock_code: str):
        """
        搜索股票代码
        
        Args:
            stock_code: 股票代码，如"600519.SH"
        """
        # 提取股票代码部分（去掉.SH后缀）
        if stock_code.endswith('.SH'):
            stock_code = stock_code[:-3]
        
        logger.info(f"搜索股票代码: {stock_code}")
        
        try:
            # 找到搜索框（左页面边的6位代码、简称输入栏）
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "inputCode"))
            )
            logger.info("找到搜索框")
            
            # 输入股票代码
            search_box.clear()
            # 模拟人类输入，逐字输入
            for char in stock_code:
                search_box.send_keys(char)
                time.sleep(0.1)  # 每次输入间隔0.1秒
            
            logger.info(f"已输入股票代码: {stock_code}")
            
            # 查找搜索按钮（搜索框右侧的搜索图标）
            search_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".search_btn.bi-search"))
            )
            logger.info("找到搜索按钮")
            
            # 点击搜索按钮
            search_button.click()
            logger.info("点击搜索按钮")
            
            # 等待搜索结果加载
            time.sleep(5)  # 延长等待时间，确保搜索结果完全加载
            
            # 保存搜索结果页面，方便分析
            with open('search_results.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("搜索结果已保存到 search_results.html")
            
            # 选择代码后向下滑动鼠标一次
            logger.info("在选择代码后向下滑动鼠标一次")
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)  # 等待页面稳定
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            # 打印页面HTML，方便调试
            with open('search_error.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("页面内容已保存到 search_error.html")
            raise
    
    def download_pdf_reports(self, max_downloads: int = 10, expected_stock_code: str = None):
        """下载PDF财报文件，并过滤出目标股票的财报"""
        logger.info(f"开始下载PDF财报，最多下载 {max_downloads} 个文件")
        
        try:
            # 等待搜索结果完全加载
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'js_announceTable'))
            )
            
            # 查找包含公告的表格
            tables = self.driver.find_elements(By.CSS_SELECTOR, 'table.table.table-hover')
            logger.info(f"找到 {len(tables)} 个包含定期报告的表格")
            
            downloaded_count = 0
            
            # 遍历所有表格
            for table in tables:
                # 查找表格中的所有行（排除表头）
                rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # 跳过表头行
                logger.info(f"表格包含 {len(rows)} 行数据")
                
                for i in range(len(rows)):
                    if downloaded_count >= max_downloads:
                        logger.info(f"已完成 {max_downloads} 个文件的下载")
                        break
                    
                    try:
                        # 每次循环都重新获取所有行，避免stale element错误
                        fresh_rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # 跳过表头行
                        if i >= len(fresh_rows):
                            logger.warning(f"第 {i+1} 行已不存在，跳过")
                            continue
                        current_row = fresh_rows[i]
                        
                        # 查找行中的所有单元格
                        cells = current_row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) < 5:
                            logger.debug(f"跳过不完整的行，只包含 {len(cells)} 个单元格")
                            continue  # 跳过不完整的行
                        
                        # 从第一个单元格提取股票代码
                        stock_code_cell = cells[0]
                        actual_stock_code = stock_code_cell.text.strip()
                        
                        # 如果指定了股票代码，检查是否匹配
                        if expected_stock_code:
                            if actual_stock_code != expected_stock_code:
                                logger.debug(f"跳过非目标股票: {actual_stock_code} (目标: {expected_stock_code})")
                                continue
                        
                        # 检查报告标题是否包含年报关键词，确保只下载年报
                        title_cell = cells[2]
                        title_text = title_cell.text.strip()
                        logger.info(f"报告标题: {title_text}")
                        # 接受包含"年报"或"年度报告"的标题
                        if '年报' not in title_text and '年度报告' not in title_text:
                            logger.info(f"跳过非年报报告: {title_text}")
                            continue
                        
                        # 从第三个单元格查找下载按钮
                        link_cell = cells[2]
                        
                        # 查找下载按钮
                        download_buttons = link_cell.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"], button.download-btn, .download-icon a')
                        
                        if download_buttons:
                            # 直接点击下载按钮
                            download_button = download_buttons[0]
                            download_href = download_button.get_attribute('href') or '无链接属性'
                            
                            logger.info(f"找到目标股票 {actual_stock_code} 的下载按钮: {download_href}")
                            
                            # 点击下载按钮
                            download_button.click()
                            logger.info("已点击下载按钮")
                            downloaded_count += 1
                            
                            # 等待下载开始
                            time.sleep(3)
                        else:
                            # 如果没有找到下载按钮，尝试找到公告标题链接（作为备选方案）
                            title_links = link_cell.find_elements(By.CSS_SELECTOR, 'a.table_titlewrap')
                            if title_links:
                                title_link = title_links[0]
                                title_text = title_link.text.strip()
                                logger.warning(f"未找到直接下载按钮，尝试点击标题链接: {title_text}")
                                
                                # 点击链接，作为备选方案
                                title_link.click()
                                time.sleep(3)
                                
                                # 切换到新窗口
                                windows = self.driver.window_handles
                                if len(windows) > 1:
                                    self.driver.switch_to.window(windows[1])
                                    
                                    try:
                                        # 在新页面查找PDF下载链接
                                        WebDriverWait(self.driver, 10).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href$=".pdf"]'))
                                        )
                                        
                                        # 查找所有PDF链接
                                        pdf_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href$=".pdf"]')
                                        if pdf_links:
                                            # 点击第一个PDF链接
                                            pdf_link = pdf_links[0]
                                            pdf_href = pdf_link.get_attribute('href')
                                            pdf_text = pdf_link.text.strip()
                                            
                                            logger.info(f"在新页面找到PDF下载链接: {pdf_text} - {pdf_href}")
                                            pdf_link.click()
                                            logger.info(f"已点击下载: {pdf_text}")
                                            downloaded_count += 1
                                    finally:
                                        # 关闭新窗口并切换回主窗口
                                        self.driver.close()
                                        self.driver.switch_to.window(windows[0])
                                    
                                    # 等待下载开始
                                    time.sleep(3)
                    
                    except Exception as e:
                        logger.error(f"处理行失败: {e}")
                        continue
            
            # 检查下载目录中的文件数量，确保日志准确
            download_dir_files = [f for f in os.listdir(self.download_dir) if f.endswith('.pdf')]
            actual_downloaded = len(download_dir_files)
            logger.info(f"下载目录中实际有 {actual_downloaded} 个PDF文件")
            
            logger.info(f"下载完成，共下载 {downloaded_count} 个文件（目录中实际存在 {actual_downloaded} 个）")
            return actual_downloaded  # 返回实际下载的文件数量
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            # 打印页面HTML，方便调试
            with open('download_error.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("页面内容已保存到 download_error.html")
            raise
    
    def select_announcement_content(self):
        """
        选择只看公告正文
        """
        logger.info("选择只看公告正文")
        
        try:
            # 查找公告正文选择选项（不滚动页面，依赖search_stock后的统一滚动）
            content_options = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'announceTypeList')]/div/div")
            logger.info(f"找到 {len(content_options)} 个公告内容选项")
            
            selected = False
            for option in content_options:
                option_text = option.text.strip()
                logger.debug(f"公告内容选项: {option_text}")
                
                if option_text == "只看公告正文":
                    # 点击选择该选项（点击圆框图标）
                    icon = option.find_element(By.CLASS_NAME, "iconcircle")
                    icon.click()
                    logger.info("已选择只看公告正文")
                    selected = True
                    break
            
            if not selected:
                logger.error("未找到只看公告正文选项")
                raise ValueError("未找到只看公告正文选项")
                
        except Exception as e:
            logger.error(f"选择只看公告正文失败: {e}")
            # 保存当前页面以分析问题
            with open('announcement_content_selection_error.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info("页面内容已保存到 announcement_content_selection_error.html")
            raise
    
    def run(self, stock_code: str, max_downloads: int = 10, report_type: str = None):
        """
        运行下载流程
        
        Args:
            stock_code: 股票代码
            max_downloads: 最大下载数量
            report_type: 报告类型，可选值：'年报', '一季报', '三季报', '半年报'。如果为None则不限制类型。
        """
        logger.info(f"开始下载 {stock_code} 的财报，报告类型: {report_type}")
        
        # 提取股票代码部分（去掉.SH后缀）
        if stock_code.endswith('.SH'):
            expected_stock_code = stock_code[:-3]
        else:
            expected_stock_code = stock_code
        
        try:
            # 打开页面
            self.open_announcement_page()
            
            # 先搜索股票
            self.search_stock(stock_code)
            
            # 选择只看公告正文
            self.select_announcement_content()
            
            # 等待1秒后再选择报告类型
            logger.info("等待1秒后选择年报...")
            time.sleep(1)
            
            # 选择报告类型
            self.select_report_type(report_type)
            
            # 等待1秒，确保页面数据加载完成
            logger.info("等待页面数据加载完成...")
            time.sleep(1)
            
            # 下载PDF文件，过滤出目标股票的财报
            downloaded_count = self.download_pdf_reports(max_downloads, expected_stock_code=expected_stock_code)
            
            logger.info(f"任务完成，共下载 {downloaded_count} 个PDF文件")
            return downloaded_count
            
        except Exception as e:
            logger.error(f"下载任务失败: {e}")
            raise

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='上交所财报下载器（Selenium版）')
    parser.add_argument('--stock-code', type=str, required=True, 
                        help='股票代码，如"600519.SH"')
    parser.add_argument('--max-downloads', type=int, default=10, 
                        help='最大下载数量')
    parser.add_argument('--download-dir', type=str, default='data/pdfs/sse',
                        help='下载目录')
    parser.add_argument('--headless', action='store_true',
                        help='使用无头模式')
    parser.add_argument('--report-type', type=str, choices=['年报', '一季报', '三季报', '半年报'],
                        default='年报',
                        help='报告类型，可选值：年报、一季报、三季报、半年报，默认选择年报')
    
    args = parser.parse_args()
    
    try:
        with SSEFinancialReportDownloader(
            download_dir=args.download_dir,
            headless=args.headless
        ) as downloader:
            downloaded_count = downloader.run(args.stock_code, args.max_downloads, args.report_type)
            
        print(f"\n下载完成！")
        print(f"股票代码: {args.stock_code}")
        print(f"报告类型: {args.report_type or '所有类型'}")
        print(f"下载文件数: {downloaded_count}")
        print(f"保存目录: {os.path.abspath(args.download_dir)}")
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断下载")
        return 1
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"\n错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
