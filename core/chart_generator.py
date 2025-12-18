# 图表生成模块
import pandas as pd
import os
import logging
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime

# 设置Plotly为离线模式
pio.renderers.default = 'iframe'

# 配置Plotly支持中文字体
pio.templates.default = 'plotly_white'
pio.templates['plotly_white'].layout.font.family = 'Microsoft YaHei, SimHei, sans-serif'
pio.templates['plotly_white'].layout.title.font.family = 'Microsoft YaHei, SimHei, sans-serif'
pio.templates['plotly_white'].layout.xaxis.title.font.family = 'Microsoft YaHei, SimHei, sans-serif'
pio.templates['plotly_white'].layout.yaxis.title.font.family = 'Microsoft YaHei, SimHei, sans-serif'

logger = logging.getLogger(__name__)

class ChartGenerator:
    """股票图表生成器"""
    
    def __init__(self, output_dir: str = "charts"):
        """初始化图表生成器"""
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_k_line_chart(self, stock_code: str, historical_data: pd.DataFrame, title: str = "", start_date: str = None, end_date: str = None) -> go.Figure:
        """生成K线图
        
        参数:
            stock_code: 股票代码
            historical_data: 历史数据，包含日期、开盘价、收盘价、最高价、最低价、成交量等字段
            title: 图表标题
            start_date: 开始日期，格式如'2020-01-01'
            end_date: 结束日期，格式如'2024-12-31'
            
        Returns:
            Plotly图表对象
        """
        try:
            if historical_data.empty:
                logger.warning(f"没有数据可生成{stock_code}的K线图")
                return None
            
            # 准备数据 - 只保留有交易数据的日期（去除非交易日）
            historical_data['日期'] = pd.to_datetime(historical_data['日期'])
            
            # 过滤日期范围
            if start_date:
                historical_data = historical_data[historical_data['日期'] >= pd.to_datetime(start_date)]
            if end_date:
                historical_data = historical_data[historical_data['日期'] <= pd.to_datetime(end_date)]
                
            # 过滤掉没有交易数据的行（保留开盘、收盘等数据不为空的行）
            trading_data = historical_data.dropna(subset=['开盘', '收盘', '最高', '最低'])
            trading_data = trading_data.sort_values('日期')
            
            if trading_data.empty:
                logger.warning(f"{start_date}到{end_date}期间没有交易数据可生成{stock_code}的K线图")
                return None
                
            logger.info(f"准备显示{stock_code}从{trading_data['日期'].min().strftime('%Y-%m-%d')}到{trading_data['日期'].max().strftime('%Y-%m-%d')}共{len(trading_data)}条记录")
            
            # 创建K线图表 - 只使用有交易数据的日期
            fig = go.Figure(data=[go.Candlestick(
                x=trading_data['日期'],
                open=trading_data['开盘'],
                high=trading_data['最高'],
                low=trading_data['最低'],
                close=trading_data['收盘'],
                increasing_line_color='red',
                decreasing_line_color='green'
            )])
            
            # 设置图表格式
            fig.update_layout(
                title=title if title else f"{stock_code} 历史K线图",
                yaxis_title='价格 (元)',
                xaxis_title='日期',
                xaxis_rangeslider_visible=True,
                xaxis_rangeslider_thickness=0.1,
                hovermode='x unified'
            )
            
            # 设置x轴为分类轴，这样所有交易日期点之间的间距相等，不会出现非交易日的空白
            fig.update_xaxes(
                type='category',
                tickformat='%Y-%m-%d',
                tickangle=-45
            )
            
            # 设置Y轴自动范围调整
            fig.update_yaxes(
                autorange=True,  # 根据当前可见数据自动调整Y轴范围
                fixedrange=False,  # 允许用户手动调整Y轴
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            # 更新X轴网格线设置（移除重复的showgrid等设置）
            fig.update_xaxes(
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            logger.info(f"成功生成{stock_code}的K线图，只显示交易日期")
            return fig
        
        except Exception as e:
            logger.error(f"生成K线图失败: {e}", exc_info=True)
            raise
    
    def generate_line_chart(self, stock_code: str, historical_data: pd.DataFrame, title: str = "") -> go.Figure:
        """生成收盘价折线图
        
        参数:
            stock_code: 股票代码
            historical_data: 历史数据，包含日期、收盘价等字段
            title: 图表标题
            
        Returns:
            Plotly图表对象
        """
        try:
            if historical_data.empty:
                logger.warning(f"没有数据可生成{stock_code}的折线图")
                return None
            
            # 准备数据 - 只保留有交易数据的日期（去除非交易日）
            historical_data['日期'] = pd.to_datetime(historical_data['日期'])
            # 过滤掉没有交易数据的行
            trading_data = historical_data.dropna(subset=['收盘'])
            trading_data = trading_data.sort_values('日期')
            
            # 创建折线图 - 只使用有交易数据的日期
            fig = go.Figure(data=[go.Scatter(
                x=trading_data['日期'],
                y=trading_data['收盘'],
                mode='lines',
                line_width=2,
                name='收盘价',
                line_color='#3498db',
                line_shape='spline',  # 使用平滑曲线
                hovertemplate='日期: %{x}<br>收盘价: %{y:.2f}'
            )])
            
            # 设置图表格式
            fig.update_layout(
                title=title if title else f"{stock_code} 历史收盘价走势",
                yaxis_title='价格 (元)',
                xaxis_title='日期',
                xaxis_rangeslider_visible=True,
                xaxis_rangeslider_thickness=0.1,
                hovermode='x unified'
            )
            
            # 设置x轴为分类轴，这样所有交易日期点之间的间距相等，不会出现非交易日的空白
            fig.update_xaxes(
                type='category',
                tickformat='%Y-%m-%d',
                tickangle=-45
            )
            
            # 设置Y轴自动范围调整
            fig.update_yaxes(
                autorange=True,  # 根据当前可见数据自动调整Y轴范围
                fixedrange=False,  # 允许用户手动调整Y轴
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            # 更新X轴网格线设置（移除重复的showgrid等设置）
            fig.update_xaxes(
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            logger.info(f"成功生成{stock_code}的折线图，只显示交易日期")
            return fig
        
        except Exception as e:
            logger.error(f"生成折线图失败: {e}")
            raise
    
    def generate_volume_chart(self, stock_code: str, historical_data: pd.DataFrame, title: str = "") -> go.Figure:
        """生成成交量柱状图
        
        参数:
            stock_code: 股票代码
            historical_data: 历史数据，包含日期、成交量等字段
            title: 图表标题
            
        Returns:
            Plotly图表对象
        """
        try:
            if historical_data.empty:
                logger.warning(f"没有数据可生成{stock_code}的成交量图")
                return None
            
            # 准备数据 - 只保留有交易数据的日期（去除非交易日）
            historical_data['日期'] = pd.to_datetime(historical_data['日期'])
            # 过滤掉没有交易数据的行
            trading_data = historical_data.dropna(subset=['开盘', '收盘', '成交量'])
            trading_data = trading_data.sort_values('日期')
            
            # 计算成交量颜色（根据涨跌）
            colors = []
            for _, row in trading_data.iterrows():
                colors.append('red' if row['收盘'] >= row['开盘'] else 'green')
            
            # 创建成交量柱状图 - 只使用有交易数据的日期
            fig = go.Figure(data=[go.Bar(
                x=trading_data['日期'],
                y=trading_data['成交量'],
                marker_color=colors,
                name='成交量',
                opacity=0.7,
                hovertemplate='日期: %{x}<br>成交量: %{y:,.0f}'
            )])
            
            # 设置图表格式
            fig.update_layout(
                title=title if title else f"{stock_code} 历史成交量",
                yaxis_title='成交量',
                xaxis_title='日期',
                xaxis_rangeslider_visible=True,
                xaxis_rangeslider_thickness=0.1,
                hovermode='x unified'
            )
            
            # 设置x轴为分类轴，这样所有交易日期点之间的间距相等，不会出现非交易日的空白
            fig.update_xaxes(
                type='category',
                tickformat='%Y-%m-%d',
                tickangle=-45
            )
            
            # 设置Y轴自动范围调整
            fig.update_yaxes(
                autorange=True,  # 根据当前可见数据自动调整Y轴范围
                fixedrange=False,  # 允许用户手动调整Y轴
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            # 更新X轴网格线设置（移除重复的showgrid等设置）
            fig.update_xaxes(
                showgrid=True, 
                gridwidth=1, 
                gridcolor='lightgray'
            )
            
            logger.info(f"成功生成{stock_code}的成交量图，只显示交易日期")
            return fig
        
        except Exception as e:
            logger.error(f"生成成交量图失败: {e}", exc_info=True)
            raise
    
    def save_chart(self, fig: go.Figure, file_name: str, file_format: str = 'html') -> str:
        """保存图表到文件
        
        参数:
            fig: Plotly图表对象
            file_name: 文件名（不含扩展名）
            file_format: 文件格式，支持png, jpg, svg, pdf等
            
        Returns:
            保存的文件路径
        """
        try:
            if not fig:
                logger.warning("没有图表可保存")
                return None
            
            # 确保文件格式有效
            valid_formats = ['png', 'jpg', 'jpeg', 'svg', 'pdf', 'html']
            if file_format.lower() not in valid_formats:
                logger.warning(f"不支持的文件格式: {file_format}，使用默认格式png")
                file_format = 'png'
            
            # 构建完整的文件路径
            file_path = os.path.join(self.output_dir, f"{file_name}.{file_format.lower()}")
            
            # 保存图表
            if file_format.lower() == 'html':
                fig.write_html(file_path, include_plotlyjs='cdn')
            else:
                fig.write_image(file_path, width=1200, height=800, scale=2)
            
            logger.info(f"图表已保存到: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存图表失败: {e}", exc_info=True)
            raise
    
    def generate_time_sharing_chart(self, stock_code: str, realtime_data: dict, title: str = "") -> go.Figure:
        """生成分时图
        
        参数:
            stock_code: 股票代码
            realtime_data: 实时数据，包含股票名称、当前价、开盘价、分时数据等
            title: 图表标题
            
        Returns:
            Plotly图表对象
        """
        try:
            # 创建模拟的分时数据（9:30-15:00，5分钟间隔）
            import pandas as pd
            from datetime import datetime, time, timedelta
            
            # 获取当前日期
            today = datetime.now().date()
            
            # 定义交易时间段（9:30-15:00）
            start_time = datetime.combine(today, time(9, 30))
            end_time = datetime.combine(today, time(15, 0))
            
            # 生成5分钟间隔的时间点
            time_points = pd.date_range(start=start_time, end=end_time, freq='5T')
            
            # 根据开盘价和当前价生成模拟价格数据
            open_price = realtime_data['open_price']
            current_price = realtime_data['current_price']
            
            # 生成随机游走的价格数据，确保最后一个价格接近当前价
            import numpy as np
            np.random.seed(42)  # 设置随机种子以获得可重现的结果
            
            # 生成随机波动（正态分布）
            volatility = 0.001  # 价格波动率
            price_changes = np.random.normal(0, volatility * open_price, len(time_points))
            
            # 计算价格序列
            prices = [open_price]
            for change in price_changes[1:]:
                prices.append(prices[-1] + change)
            
            # 调整最后一个价格为当前价
            prices[-1] = current_price
            
            # 创建DataFrame
            df = pd.DataFrame({'time': time_points, 'price': prices})
            
            # 创建分时图
            fig = go.Figure()
            
            # 添加分时线
            fig.add_trace(go.Scatter(
                x=df['time'],
                y=df['price'],
                mode='lines',
                line=dict(color='#1f77b4', width=2),
                name='价格',
                hovertemplate='时间: %{x|%H:%M}<br>价格: %{y:.2f}'
            ))
            
            # 添加开盘价水平线
            fig.add_trace(go.Scatter(
                x=df['time'],
                y=[open_price] * len(df),
                mode='lines',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                name='开盘价',
                hovertemplate='开盘价: %{y:.2f}'
            ))
            
            # 添加当前价标记点
            fig.add_trace(go.Scatter(
                x=[df['time'].iloc[-1]],
                y=[current_price],
                mode='markers',
                marker=dict(color='#2ca02c', size=10),
                name='当前价',
                hovertemplate='当前价: %{y:.2f}'
            ))
            
            # 设置图表格式
            fig.update_layout(
                title=title if title else f"{realtime_data['name']} ({stock_code}) 分时图",
                yaxis_title='价格 (元)',
                xaxis_title='时间',
                xaxis_rangeslider_visible=True,
                xaxis_rangeslider_thickness=0.1,
                hovermode='x unified',
                height=600,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            # 设置时间轴格式
            fig.update_xaxes(
                tickformat='%H:%M',
                tickangle=-45,
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            )
            
            # 设置价格轴范围
            price_min = min(df['price']) * 0.998
            price_max = max(df['price']) * 1.002
            fig.update_yaxes(
                range=[price_min, price_max],
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                fixedrange=False
            )
            
            # 添加涨跌幅信息
            change = realtime_data['change']
            change_percent = realtime_data['change_percent']
            color = 'red' if change >= 0 else 'green'
            
            # 使用Plotly的注释功能添加涨跌幅信息
            fig.add_annotation(
                x=0.02,
                y=0.95,
                xref='paper',
                yref='paper',
                text=f'当前价: {current_price:.2f}元<br>涨跌额: {change:+.2f}元<br>涨跌幅: {change_percent:+.2f}%',
                showarrow=False,
                font=dict(size=12, color='black'),
                bgcolor='rgba(245, 222, 179, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1,
                borderpad=10,
                opacity=0.9
            )
            
            logger.info(f"成功生成{stock_code}的分时图")
            return fig
            
        except Exception as e:
            logger.error(f"生成分时图失败: {e}", exc_info=True)
            raise
    
    def generate_and_save_all_charts(self, stock_code: str, historical_data: pd.DataFrame) -> dict:
        """生成并保存所有类型的图表
        
        参数:
            stock_code: 股票代码
            historical_data: 历史数据
            
        Returns:
            包含所有保存图表路径的字典
        """
        try:
            saved_charts = {}
            
            # 生成并保存K线图
            k_line_fig = self.generate_k_line_chart(stock_code, historical_data)
            if k_line_fig:
                saved_charts['k_line'] = self.save_chart(k_line_fig, f"{stock_code}_k_line")
            
            # 生成并保存收盘价折线图
            line_fig = self.generate_line_chart(stock_code, historical_data)
            if line_fig:
                saved_charts['line'] = self.save_chart(line_fig, f"{stock_code}_line")
            
            # 生成并保存成交量图
            volume_fig = self.generate_volume_chart(stock_code, historical_data)
            if volume_fig:
                saved_charts['volume'] = self.save_chart(volume_fig, f"{stock_code}_volume")
            
            return saved_charts
            
        except Exception as e:
            logger.error(f"生成并保存所有图表失败: {e}", exc_info=True)
            raise
