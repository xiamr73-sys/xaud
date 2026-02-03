import streamlit as st
import akshare as ak
import pandas as pd
import strategies
import datetime
from tqdm import tqdm
import time
import concurrent.futures
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from chanlun_simple import ChanlunSimple

# 版本信息
APP_VERSION = "v1.2.0"
LAST_UPDATED = datetime.datetime.now().strftime("%Y-%m-%d")

# 设置页面配置
st.set_page_config(
    page_title=f"A股 智能选股助手 {APP_VERSION}",
    page_icon="📈",
    layout="wide"
)

# ... (辅助函数保持不变)

def process_stock(stock_info):
    """
    单个股票处理函数 (用于并行处理)
    """
    symbol = stock_info['code']
    name = stock_info['name']
    
    try:
        # 优化：只获取最近半年的数据，减少数据传输量
        # 今天的日期
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        # 半年前的日期 (180天)
        start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y%m%d")
        
        fetch_start = time.time() # 计时开始
        
        # 尝试获取数据
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            if df.empty:
                df = get_stock_data(symbol)
            else:
                df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
        except:
            df = get_stock_data(symbol)
            
        fetch_time = time.time() - fetch_start # 计时结束
        
        if df.empty or len(df) < 60:
            return None
            
        # 计算指标
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        df = strategies.calculate_kdj(df)
        
        latest = df.iloc[-1]
        matched_patterns = []

        if strategies.check_comprehensive_strategy(df):
            matched_patterns.append("综合策略")
        if strategies.check_old_duck_head(df):
            matched_patterns.append("老鸭头")
        if strategies.check_platform_breakout(df):
            matched_patterns.append("平台突破")
        if strategies.check_dragon_turns_head(df):
            matched_patterns.append("龙回头")
        
        if matched_patterns:
            return {
                '代码': symbol,
                '名称': name,
                '最新价': latest['close'],
                '日期': latest['date'],
                '匹配模式': ", ".join(matched_patterns),
                '耗时': fetch_time # 返回耗时
            }
        
        # 即使没有匹配模式，如果是为了调试延迟，也可以考虑返回耗时（但在并发模式下不好统计）
        # 这里我们只统计匹配到的或者抽样统计
            
    except Exception:
        return None
    return None

def plot_stock_detail(symbol, name):
    """绘制K线图并标注止盈止损"""
    try:
        # 获取数据 (获取稍长一点的时间以计算均线)
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y%m%d")
        
        df = None
        # 1. 尝试主要接口
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        except Exception:
            df = None
            
        # 2. 如果主要接口失败或为空，尝试备用接口
        if df is None or df.empty:
             df = get_stock_data(symbol)
             
        if df is None or df.empty:
            st.error("无法获取该股票历史数据 (数据源连接失败)")
            return

        # 标准化列名，适应不同接口返回的列数差异
        # 东方财富接口通常返回 11 列，新浪接口返回 9-10 列
        # 无论哪种，我们只需要核心的 date, open, close, high, low, volume
        # 先尝试将 columns 赋值，如果失败（长度不匹配），则尝试自动推断
        
        expected_cols_11 = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
        expected_cols_sina = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'pct_chg']
        
        try:
            if len(df.columns) == 11:
                df.columns = expected_cols_11
            elif len(df.columns) >= 9:
                # 尝试匹配新浪的格式 (注意新浪 high/low 顺序可能不同，这里假设 get_stock_data 已经处理过或者 akshare 返回顺序固定)
                # 最好是依赖 get_stock_data 中已经统一好的列名，如果 get_stock_data 返回的是 dataframe，它应该有列名
                # 如果 df 来自 get_stock_data，列名已经是英文的了，不需要重命名
                if 'open' not in df.columns: 
                    # 只有当列名不是英文时才重命名
                    # 这是一个简单的 fallback，假设 9 列是新浪旧版
                    df.columns = expected_cols_sina[:len(df.columns)]
            else:
                st.error(f"数据格式异常，列数: {len(df.columns)}")
                return
        except Exception as e:
            # 如果重命名失败，打印一下当前的列名以便调试 (实际部署中看不到 print，所以尝试容错)
            pass
            
        # 确保 date 是 datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
             # 尝试第一列作为日期
             df.rename(columns={df.columns[0]: 'date'}, inplace=True)
             df['date'] = pd.to_datetime(df['date'])
             
        # 确保其他列存在
        required_cols = ['open', 'close', 'high', 'low', 'volume']
        if not all(col in df.columns for col in required_cols):
             st.error("数据缺失关键列 (Open/Close/High/Low)")
             return
        
        # 计算均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # 只展示最近 60 天，以免图表过于拥挤
        plot_df = df.tail(60).copy()
        
        if plot_df.empty:
            st.warning("数据不足，无法绘图")
            return

        # 止盈止损逻辑 (基于最新收盘价)
        latest_close = plot_df.iloc[-1]['close']
        stop_loss_price = latest_close * 0.95  # 止损 -5%
        take_profit_price = latest_close * 1.10 # 止盈 +10%
        
        # 创建图表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, subplot_titles=(f'{name} ({symbol}) 日线', '成交量'), 
                            row_width=[0.2, 0.7])

        # K线图
        fig.add_trace(go.Candlestick(
            x=plot_df['date'],
            open=plot_df['open'],
            high=plot_df['high'],
            low=plot_df['low'],
            close=plot_df['close'],
            name='K线'
        ), row=1, col=1)

        # 均线
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma5'], line=dict(color='black', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma10'], line=dict(color='orange', width=1), name='MA10'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma20'], line=dict(color='purple', width=1), name='MA20'), row=1, col=1)

        # 止盈止损线 (虚线)
        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="green", annotation_text=f"止损 (-5%): {stop_loss_price:.2f}", row=1, col=1)
        fig.add_hline(y=take_profit_price, line_dash="dash", line_color="red", annotation_text=f"止盈 (+10%): {take_profit_price:.2f}", row=1, col=1)

        # 成交量
        fig.add_trace(go.Bar(x=plot_df['date'], y=plot_df['volume'], name='成交量'), row=2, col=1)

        # 布局设置
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=600,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # 补充信息
        st.caption(f"当前价格: {latest_close:.2f} | 建议止损: {stop_loss_price:.2f} | 建议止盈: {take_profit_price:.2f}")
        
    except Exception as e:
        st.error(f"绘图失败: {e}")

def plot_chanlun(symbol, name):
    """绘制缠论分析图"""
    try:
        # 获取足够长的数据以进行包含处理和笔识别
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=365*2)).strftime("%Y%m%d")
        
        with st.spinner("正在计算缠论分型与笔..."):
            df = None
            try:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            except Exception:
                df = None
            
            if df is None or df.empty:
                 df = get_stock_data(symbol)
                 
            if df is None or df.empty:
                st.error("无法获取该股票历史数据 (数据源连接失败)")
                return

            # 标准化列名逻辑 (与 plot_stock_detail 保持一致，建议后续封装)
            expected_cols_11 = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            expected_cols_sina = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover', 'pct_chg']
            
            try:
                if len(df.columns) == 11:
                    df.columns = expected_cols_11
                elif len(df.columns) >= 9:
                    if 'open' not in df.columns: 
                        df.columns = expected_cols_sina[:len(df.columns)]
                else:
                    st.error(f"数据格式异常，列数: {len(df.columns)}")
                    return
            except Exception:
                pass
                
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                 df.rename(columns={df.columns[0]: 'date'}, inplace=True)
                 df['date'] = pd.to_datetime(df['date'])
            
            # 缠论计算
            cl = ChanlunSimple(df)
            cl.process_inclusion()
            cl.find_fenxing()
            bi_list = cl.find_bi()
            
            # 绘图数据 (取最近半年的K线展示，但笔需要基于全量计算)
            plot_start_date = df.iloc[-120]['date'] if len(df) > 120 else df.iloc[0]['date']
            plot_df = df[df['date'] >= plot_start_date].copy()
            
            # 创建图表
            fig = make_subplots(rows=1, cols=1, subplot_titles=(f'{name} ({symbol}) 缠论分析 (包含处理+笔)',))

            # 1. 原始K线 (半透明背景)
            fig.add_trace(go.Candlestick(
                x=plot_df['date'],
                open=plot_df['open'],
                high=plot_df['high'],
                low=plot_df['low'],
                close=plot_df['close'],
                name='原始K线',
                opacity=0.5
            ))
            
            # 2. 绘制笔 (Bi)
            # 筛选出在绘图时间范围内的笔
            valid_bi = []
            for bi in bi_list:
                if bi['end_date'] >= plot_start_date:
                    valid_bi.append(bi)
            
            # 将笔连接成一条连续的线 (ZigZag style)
            if valid_bi:
                bi_x = []
                bi_y = []
                # 添加第一笔的起点
                bi_x.append(valid_bi[0]['start_date'])
                bi_y.append(valid_bi[0]['start_price'])
                
                for bi in valid_bi:
                    bi_x.append(bi['end_date'])
                    bi_y.append(bi['end_price'])
                
                fig.add_trace(go.Scatter(
                    x=bi_x, 
                    y=bi_y, 
                    mode='lines+markers',
                    line=dict(color='yellow', width=2),
                    marker=dict(size=4),
                    name='笔 (Bi)'
                ))
                
                # 标注笔的端点价格
                fig.add_trace(go.Scatter(
                    x=bi_x,
                    y=bi_y,
                    mode='text',
                    text=[f"{y:.2f}" for y in bi_y],
                    textposition="top center",
                    name='端点价格'
                ))

            # 布局设置
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"识别到 {len(valid_bi)} 笔 (仅展示最近 120 个交易日范围内)")

    except Exception as e:
        st.error(f"缠论分析失败: {e}")

def run_scan(stock_list, progress_bar, status_text):
    results = []
    total = len(stock_list)
    stocks_to_process = stock_list.to_dict('records')
    max_workers = 5 
    
    completed = 0
    total_fetch_time = 0
    fetch_count = 0
    
    # 占位符用于显示实时指标
    metrics_placeholder = st.empty()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {executor.submit(process_stock, stock): stock for stock in stocks_to_process}
        
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            completed += 1
            
            progress = completed / total
            progress_bar.progress(progress)
            status_text.text(f"正在分析: {stock['code']} {stock['name']} ({completed}/{total})")
            
            try:
                result = future.result()
                if result:
                    results.append(result)
                    if '耗时' in result:
                        total_fetch_time += result['耗时']
                        fetch_count += 1
                        avg_time = total_fetch_time / fetch_count
                        metrics_placeholder.caption(f"⚡️ 平均网络延迟: {avg_time:.2f}s / 股")
                        
            except Exception:
                pass
            
    return pd.DataFrame(results)

@st.cache_data(ttl=3600)
def get_sector_list():
    """获取板块列表 (缓存 1 小时)"""
    try:
        # 优先尝试新浪接口，因为它在当前环境似乎更稳定
        sectors = ak.stock_sector_spot(indicator="新浪行业")
        return sectors['板块'].tolist()
    except Exception:
        # 备用：生成一些静态的常见板块，防止完全无法使用
        return ["半导体", "白酒", "银行", "证券", "医药商业", "房地产开发", "电力行业", "汽车整车"]

def get_sector_stocks(sector_name):
    """获取指定板块的股票列表"""
    try:
        sectors = ak.stock_sector_spot(indicator="新浪行业")
        matched_sectors = sectors[sectors['板块'].str.contains(sector_name)]
        
        if matched_sectors.empty:
            return None, f"未找到名称包含 '{sector_name}' 的板块"
            
        target_sector = matched_sectors.iloc[0]
        sector_label = target_sector['label']
        sector_real_name = target_sector['板块']
        
        details = ak.stock_sector_detail(sector=sector_label)
        if details.empty:
            return None, "该板块没有成分股数据"
            
        return details[['code', 'name']], sector_real_name
    except Exception as e:
        return None, str(e)

def get_stock_data(symbol):
    """尝试多种接口获取数据"""
    # 1. 尝试东方财富接口 (ak.stock_zh_a_hist) - 数据最全
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        if not df.empty:
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            return df
    except:
        pass
        
    # 2. 尝试新浪接口 (ak.stock_zh_a_daily) - 备用
    try:
        # 新浪接口需要加前缀 sz/sh
        prefix_symbol = ""
        if symbol.startswith("6"): prefix_symbol = f"sh{symbol}"
        elif symbol.startswith("0") or symbol.startswith("3"): prefix_symbol = f"sz{symbol}"
        else: prefix_symbol = symbol
        
        df = ak.stock_zh_a_daily(symbol=prefix_symbol, adjust="qfq")
        if not df.empty:
            # 新浪列名: date, open, high, low, close, volume, amount, outstanding_share, turnover
            # 我们需要标准化列名以适配 strategies
            # 注意：新浪数据可能没有 pct_chg (涨跌幅)，需要自己计算
            df = df.rename(columns={'outstanding_share': 'turnover'}) # 这里的 turnover 含义不同，暂且忽略
            
            # 简单计算涨跌幅
            df['pct_chg'] = df['close'].pct_change() * 100
            df['pct_chg'] = df['pct_chg'].fillna(0)
            
            return df
    except:
        pass
        
    return pd.DataFrame() # 均失败返回空


@st.cache_data(ttl=600) # 缓存 10 分钟
def get_sector_fund_flow():
    """获取板块资金流向数据"""
    try:
        # 尝试获取行业资金流向
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df.empty:
             raise ValueError("Empty data from EM")
        return df[['序号', '名称', '今日涨跌幅', '主力净流入-净额', '主力净流入-净占比']]
    except Exception:
        # Fallback 1: 尝试概念资金流，如果行业不行的话
        try:
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
            if not df.empty:
                return df[['序号', '名称', '今日涨跌幅', '主力净流入-净额', '主力净流入-净占比']]
        except:
            pass
            
        # Fallback 2: 尝试同花顺行业资金流 (10jqka)
        try:
            df = ak.stock_fund_flow_industry(symbol="即时")
            if not df.empty:
                # 同花顺字段: 行业, 行业指数, 涨跌幅, 流入资金, 流出资金, 净额, ...
                # 映射到我们的标准列名
                df = df.rename(columns={
                    '行业': '名称', 
                    '涨跌幅': '今日涨跌幅', 
                    '净额': '主力净流入-净额'
                })
                # 同花顺可能没有 '主力净流入-净占比'，我们用 '净额' 替代或计算
                # 简单起见，这里只保留共有字段
                df['序号'] = range(1, len(df) + 1)
                df['主力净流入-净占比'] = 0 # 缺失填充
                return df[['序号', '名称', '今日涨跌幅', '主力净流入-净额', '主力净流入-净占比']]
        except:
            pass
            
        # Fallback 3: 返回一个空的 DataFrame 结构，而不是 None，方便后续判断
        # 或者尝试其他接口，例如 ak.stock_individual_fund_flow_rank_jg_eastmoney() 
        # 但 akshare 对板块资金流的接口比较单一，主要依赖 EM。
        
        # 最后的手段：构造模拟数据（仅演示用，正式环境不建议，或者显示更友好的错误）
        # return pd.DataFrame(columns=['序号', '名称', '今日涨跌幅', '主力净流入-净额', '主力净流入-净占比'])
        return None
    return None

# --- 核心功能模块 ---



def run_backtest_logic(days_lookback, sample_size, progress_bar, status_text):
    try:
        hs300 = ak.index_stock_cons(symbol="000300")
        stock_list = hs300[['stock_code', 'stock_name']]
        stock_list.columns = ['code', 'name']
        stock_list = stock_list.head(sample_size)
    except Exception:
        stock_list = ak.stock_info_a_code_name().head(sample_size)

    stats = {
        "综合策略": {"signals": 0, "wins": 0, "total_return": 0.0},
        "老鸭头": {"signals": 0, "wins": 0, "total_return": 0.0},
        "平台突破": {"signals": 0, "wins": 0, "total_return": 0.0},
        "龙回头": {"signals": 0, "wins": 0, "total_return": 0.0}
    }
    
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days_lookback + 60)).strftime("%Y%m%d")
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    total = len(stock_list)
    for index, row in stock_list.iterrows():
        progress_bar.progress((index + 1) / total)
        symbol = row['code']
        status_text.text(f"回测中: {symbol} {row['name']}")
        
        try:
            df = get_stock_data(symbol)
            if df.empty or len(df) < 60: continue
            
            # df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            df = strategies.calculate_kdj(df)
            
            analysis_start_idx = len(df) - days_lookback
            if analysis_start_idx < 60: analysis_start_idx = 60
            
            for i in range(analysis_start_idx, len(df) - 5):
                current_df = df.iloc[:i+1]
                future_df = df.iloc[i+1:i+6]
                
                if future_df.empty: continue
                
                entry_price = current_df.iloc[-1]['close']
                max_price = future_df['high'].max()
                max_return = (max_price - entry_price) / entry_price
                is_win = max_return > 0.03
                
                if strategies.check_comprehensive_strategy(current_df):
                    stats["综合策略"]["signals"] += 1
                    if is_win: stats["综合策略"]["wins"] += 1
                    stats["综合策略"]["total_return"] += max_return

                if strategies.check_old_duck_head(current_df):
                    stats["老鸭头"]["signals"] += 1
                    if is_win: stats["老鸭头"]["wins"] += 1
                    stats["老鸭头"]["total_return"] += max_return

                if strategies.check_platform_breakout(current_df):
                    stats["平台突破"]["signals"] += 1
                    if is_win: stats["平台突破"]["wins"] += 1
                    stats["平台突破"]["total_return"] += max_return
                    
                if strategies.check_dragon_turns_head(current_df):
                    stats["龙回头"]["signals"] += 1
                    if is_win: stats["龙回头"]["wins"] += 1
                    stats["龙回头"]["total_return"] += max_return
                    
        except Exception:
            continue
            
    return stats

# --- 页面 UI ---
st.title(f"📈 A股 智能选股助手 {APP_VERSION}")
st.caption(f"上次更新: {LAST_UPDATED}")
st.markdown("基于技术指标和经典K线形态的自动化扫描工具")

# 侧边栏
with st.sidebar:
    st.header("功能选择")
    app_mode = st.radio("选择模式", ["K线扫描", "策略回测", "情绪监控", "板块资金看板", "缠论分析"])
    
    st.markdown("---")
    st.markdown("### 关于")
    st.markdown("本工具支持：\n- 综合策略\n- 老鸭头\n- 平台突破\n- 龙回头")

if app_mode == "K线扫描":
    st.header("🔍 股票扫描")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        # 获取板块列表
        sector_list = get_sector_list()
        selected_sector = st.selectbox("选择扫描板块", ["全市场 (前50只演示)", "全市场 (全量-很慢)", "自定义输入"] + sector_list)
        
        custom_sector = ""
        if selected_sector == "自定义输入":
            custom_sector = st.text_input("请输入板块名称 (如: 半导体)")
            
    with col2:
        st.write("") # Spacer
        st.write("")
        start_btn = st.button("开始扫描", type="primary")

    if start_btn:
        stock_list = None
        limit_msg = ""
        
        # ... (list generation logic same as before)
        if selected_sector == "全市场 (前50只演示)":
            try:
                stock_list = ak.stock_info_a_code_name().head(50)
                limit_msg = " (演示模式：仅扫描前 50 只)"
            except Exception as e:
                st.error(f"获取股票列表失败: {e}")
        elif selected_sector == "全市场 (全量-很慢)":
            try:
                stock_list = ak.stock_info_a_code_name()
                limit_msg = " (全量模式)"
            except Exception as e:
                st.error(f"获取股票列表失败: {e}")
        else:
            sector_name = custom_sector if selected_sector == "自定义输入" else selected_sector
            if not sector_name:
                st.warning("请输入有效的板块名称")
            else:
                with st.spinner(f"正在获取 [{sector_name}] 成分股..."):
                    stocks, real_name = get_sector_stocks(sector_name)
                    if stocks is not None:
                        stock_list = stocks
                        limit_msg = f" (板块: {real_name})"
                    else:
                        st.error(real_name)

        if stock_list is not None:
            st.info(f"开始扫描 {len(stock_list)} 只股票{limit_msg}...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            result_df = run_scan(stock_list, progress_bar, status_text)
            
            progress_bar.progress(100)
            status_text.text("扫描完成！")
            
            if not result_df.empty:
                st.success(f"共发现 {len(result_df)} 只符合条件的股票")
                # 保存结果到 session_state
                st.session_state['scan_results'] = result_df
            else:
                st.warning("未找到符合条件的股票。")
                st.session_state['scan_results'] = pd.DataFrame()

    # 展示结果 (如果存在)
    if 'scan_results' in st.session_state and not st.session_state['scan_results'].empty:
        result_df = st.session_state['scan_results']
        st.dataframe(result_df, use_container_width=True)
        
        # 下载按钮
        csv = result_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "下载结果 CSV",
            csv,
            "scan_results.csv",
            "text/csv",
            key='download-csv'
        )
        
        st.markdown("---")
        st.subheader("📊 详情分析 (止盈止损)")
        
        # 详情选择
        stock_options = result_df.apply(lambda x: f"{x['代码']} {x['名称']}", axis=1).tolist()
        selected_option = st.selectbox("点击下方列表选择要查看的股票:", ["请选择..."] + stock_options)
        
        if selected_option and selected_option != "请选择...":
            code = selected_option.split(" ")[0]
            name = selected_option.split(" ")[1]
            plot_stock_detail(code, name)

elif app_mode == "策略回测":
    st.header("🔙 策略回测")
    st.info("使用沪深300成分股作为样本，测试过去一段时间的策略表现。")
    
    col1, col2 = st.columns(2)
    with col1:
        lookback = st.slider("回测天数", 30, 180, 90)
    with col2:
        sample_size = st.slider("样本数量 (只)", 10, 300, 50)
        
    if st.button("开始回测", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        stats = run_backtest_logic(lookback, sample_size, progress_bar, status_text)
        
        progress_bar.progress(100)
        status_text.text("回测完成")
        
        st.subheader("回测结果")
        st.caption("胜率标准：信号出现后未来 5 天内最高涨幅 > 3%")
        
        # 展示结果
        results_data = []
        for name, data in stats.items():
            signals = data["signals"]
            win_rate = 0
            avg_return = 0
            if signals > 0:
                win_rate = (data["wins"] / signals) * 100
                avg_return = (data["total_return"] / signals) * 100
            
            results_data.append({
                "策略名称": name,
                "触发信号次数": signals,
                "胜率 (%)": f"{win_rate:.2f}%",
                "平均最高涨幅 (%)": f"{avg_return:.2f}%"
            })
            
        st.table(pd.DataFrame(results_data))

elif app_mode == "情绪监控":
    st.header("📰 市场情绪监控")
    
    if st.button("刷新今日情绪", type="primary"):
        with st.spinner("正在获取新闻数据..."):
            try:
                # CCTV - 优先获取今天，如果为空（例如早上），则获取昨天
                st.subheader("📺 新闻联播 (宏观)")
                today_str = datetime.datetime.now().strftime("%Y%m%d")
                cctv_df = ak.news_cctv(date=today_str)
                
                if cctv_df.empty:
                    yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d")
                    cctv_df = ak.news_cctv(date=yesterday_str)
                    if not cctv_df.empty:
                        st.caption(f"今日数据暂未更新，显示昨日 ({yesterday_str}) 数据")
                
                if not cctv_df.empty:
                    for i, row in cctv_df.head(3).iterrows():
                        with st.expander(f"{row['title']}"):
                            st.write(row['content'])
                else:
                    st.write("暂无近期新闻联播数据。")
                
                # 个股/市场新闻
                st.subheader("🔥 关键词扫描")
                # 使用贵州茅台作为示例，或者尝试获取更广泛的
                news_df = ak.stock_news_em(symbol="600519")
                keywords = ["上涨", "拉升", "涨停", "利好", "突破", "暴涨", "资金", "买入", "增长"]
                
                found_news = []
                for index, row in news_df.iterrows():
                    title = row.get('title', '')
                    content = row.get('content', '')
                    time_str = row.get('public_time', '')
                    full_text = f"{title} {content}"
                    
                    if any(k in full_text for k in keywords):
                        found_news.append({"时间": time_str, "标题": title, "内容": content})
                        if len(found_news) >= 10: break
                
                if found_news:
                    for news in found_news:
                        st.markdown(f"**[{news['时间']}]** {news['标题']}")
                else:
                    st.info("在示例源中未扫描到包含 '暴涨/利好' 等关键词的重磅新闻。")
                    
            except Exception as e:
                st.error(f"获取新闻失败: {e}")

elif app_mode == "板块资金看板":
    st.header("💰 板块资金流向看板")
    st.caption("数据来源：东方财富 (实时/盘后)")
    
    if st.button("刷新数据", type="primary"):
        with st.spinner("正在获取全市场板块资金流向..."):
            df_fund = get_sector_fund_flow()
            
            if df_fund is not None and not df_fund.empty:
                # 简单的数据清洗和排序
                # 假设 '主力净流入-净额' 是带单位的字符串，为了排序可能需要处理
                # 这里先直接展示原始数据，通常已经是排好序的
                
                # 尝试转换 '主力净流入-净额' 为数值进行着色
                def color_fund_flow(val):
                    try:
                        # 简单的启发式判断：包含 '-' 且不是负号开头可能是异常，但这里通常是负数
                        if '亿' in str(val) or '万' in str(val):
                            # 带单位，难以直接比较，但可以判断正负
                            if str(val).startswith('-'):
                                return 'color: green' # 跌/流出为绿
                            else:
                                return 'color: red'   # 涨/流入为红
                        return ''
                    except:
                        return ''

                st.subheader("行业板块资金流向 (今日)")
                
                # 交互式表格
                st.dataframe(
                    df_fund,
                    use_container_width=True,
                    height=600
                )
                
                st.info("提示：点击表头可以进行排序。红色代表资金流入，绿色代表资金流出。")
                
            else:
                st.warning("暂未获取到板块资金流向数据，可能是接口访问受限或非交易时间。")
                st.markdown("""
                **可能的原因：**
                1. 东方财富接口反爬虫限制（云端常见）。
                2. 当前非交易时间，数据未更新。
                """)

elif app_mode == "缠论分析":
    st.header("☯️ 缠论 K 线分析")
    st.markdown("输入股票代码或名称，自动识别**顶底分型**与**笔 (Bi)**。")
    
    # 搜索框
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("请输入股票代码或名称 (例如: 600519 或 贵州茅台)", placeholder="支持模糊搜索...")
    with col2:
        st.write("")
        st.write("")
        search_btn = st.button("开始分析", type="primary")
        
    if search_btn and query:
        # 1. 尝试直接作为代码
        symbol = None
        name = ""
        
        if query.isdigit() and len(query) == 6:
            symbol = query
            name = query # 暂定
        else:
            # 2. 模糊搜索名称
            try:
                stock_info = ak.stock_info_a_code_name()
                # 过滤
                matched = stock_info[stock_info['code'].str.contains(query) | stock_info['name'].str.contains(query)]
                
                if matched.empty:
                    st.error(f"未找到匹配 '{query}' 的股票。")
                elif len(matched) > 1:
                    st.warning("找到多只匹配股票，默认分析第一只：")
                    st.dataframe(matched.head(5))
                    symbol = matched.iloc[0]['code']
                    name = matched.iloc[0]['name']
                else:
                    symbol = matched.iloc[0]['code']
                    name = matched.iloc[0]['name']
            except Exception as e:
                st.error(f"搜索股票失败: {e}")
                
        if symbol:
            st.success(f"正在分析: {name} ({symbol})")
            plot_chanlun(symbol, name)
            
            st.markdown("""
            ### 图例说明
            - **K线**: 原始行情数据 (半透明背景)
            - **黄色连线**: 识别出的“笔” (Bi)
            - **端点数字**: 笔的顶/底价格
            
            > **注意**: 
            > 1. 本功能使用了**简化版缠论算法** (包含处理 + 顶底分型 + 笔)。
            > 2. “笔”的定义严格遵循“顶底分型之间至少包含一根独立K线”的规则。
            > 3. 仅供技术分析参考，不作为买卖建议。
            """)
