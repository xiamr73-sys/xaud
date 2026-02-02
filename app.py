import streamlit as st
import akshare as ak
import pandas as pd
import strategies
import datetime
from tqdm import tqdm
import time
import concurrent.futures

# 设置页面配置
st.set_page_config(
    page_title="A股 智能选股助手",
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
        
        # 字段重命名以更友好显示
        # 原始字段通常包括: 序号, 名称, 今日涨跌幅, 主力净流入-净额, 主力净流入-净占比, ...
        # 我们只取关键字段
        if not df.empty:
            # 确保数值列是数字类型
            numeric_cols = ['今日涨跌幅', '主力净流入-净额', '主力净流入-净占比', '超大单净流入-净额', '大单净流入-净额', '中单净流入-净额', '小单净流入-净额']
            for col in numeric_cols:
                if col in df.columns:
                    # 去掉单位等非数字字符并转换 (akshare返回的通常已经是处理过的，但为了保险)
                    # 这里 akshare 返回的通常是 float 或带单位字符串，视版本而定
                    # 假设是 float 或可以直接转换
                    pass
            
            # 简单处理单位，如果是以 '万' 或 '亿' 结尾的字符串，需要转换
            # 目前 akshare 这个接口返回的通常是带单位的字符串或数字
            # 我们先原样返回，由 dataframe 展示
            
            # 排序：默认按主力净流入净额降序
            # 注意：如果列是字符串，排序可能不准。
            # 这里先假设 akshare 返回的是易读格式。
            
            return df[['序号', '名称', '今日涨跌幅', '主力净流入-净额', '主力净流入-净占比']]
            
    except Exception as e:
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

st.title("📈 A股 智能选股助手")
st.markdown("基于技术指标和经典K线形态的自动化扫描工具")

# 侧边栏
with st.sidebar:
    st.header("功能选择")
    app_mode = st.radio("选择模式", ["K线扫描", "策略回测", "情绪监控", "板块资金看板"])
    
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
        
        # 检查网络连接 (简单检查)
        # try:
        #    get_stock_data("000001")
        # except Exception as e:
        #     st.error(f"无法连接到数据源...\n错误详情: {e}")
        #     st.stop()
        
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
                        st.error(real_name) # 这里 real_name 是错误信息

        if stock_list is not None:
            st.info(f"开始扫描 {len(stock_list)} 只股票{limit_msg}...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            result_df = run_scan(stock_list, progress_bar, status_text)
            
            progress_bar.progress(100)
            status_text.text("扫描完成！")
            
            if not result_df.empty:
                st.success(f"共发现 {len(result_df)} 只符合条件的股票")
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
            else:
                st.warning("未找到符合条件的股票。")

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
