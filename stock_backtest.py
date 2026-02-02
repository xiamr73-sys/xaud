import akshare as ak
import pandas as pd
import strategies
from tqdm import tqdm
import datetime
import numpy as np

def run_backtest(days_lookback=90, sample_size=50):
    print(f"开始回测: 过去 {days_lookback} 天, 样本数: {sample_size} 只股票...")
    
    try:
        # 获取沪深300成分股作为样本，代表性较强且质量较好
        print("获取沪深300成分股作为回测样本...")
        hs300 = ak.index_stock_cons(symbol="000300")
        stock_list = hs300[['stock_code', 'stock_name']]
        stock_list.columns = ['code', 'name']
        
        # 限制样本数量
        stock_list = stock_list.head(sample_size)
    except Exception as e:
        print(f"获取成分股失败，使用全市场前 {sample_size} 只: {e}")
        stock_list = ak.stock_info_a_code_name().head(sample_size)

    # 统计数据
    stats = {
        "综合策略": {"signals": 0, "wins": 0, "total_return": 0.0},
        "老鸭头": {"signals": 0, "wins": 0, "total_return": 0.0},
        "平台突破": {"signals": 0, "wins": 0, "total_return": 0.0},
        "龙回头": {"signals": 0, "wins": 0, "total_return": 0.0}
    }
    
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days_lookback + 60)).strftime("%Y%m%d")
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    for index, row in tqdm(stock_list.iterrows(), total=stock_list.shape[0]):
        symbol = row['code']
        
        try:
            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            if df.empty or len(df) < 60: continue
            
            df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_chg', 'change', 'turnover']
            
            # 计算指标
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            df = strategies.calculate_kdj(df)
            
            # 遍历回测窗口（排除最近 5 天，因为无法验证未来收益）
            # 我们只在过去 days_lookback 天内寻找信号
            
            analysis_start_idx = len(df) - days_lookback
            if analysis_start_idx < 60: analysis_start_idx = 60
            
            for i in range(analysis_start_idx, len(df) - 5):
                # 切片获取截止到 i 天的数据
                current_df = df.iloc[:i+1]
                future_df = df.iloc[i+1:i+6] # 未来 5 天
                
                if future_df.empty: continue
                
                # 计算未来 5 天的最大收益率
                entry_price = current_df.iloc[-1]['close']
                max_price = future_df['high'].max()
                max_return = (max_price - entry_price) / entry_price
                
                # 判定胜负标准：未来 5 天内最高涨幅超过 3% 算胜 (简单标准)
                is_win = max_return > 0.03
                
                # 检查各个策略
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
                    
        except Exception as e:
            continue

    print("\n====== 回测结果 (过去 3 个月, 未来 5 天涨幅 > 3% 算胜) ======")
    for name, data in stats.items():
        signals = data["signals"]
        if signals > 0:
            win_rate = (data["wins"] / signals) * 100
            avg_return = (data["total_return"] / signals) * 100
            print(f"[{name}] 信号数: {signals}, 胜率: {win_rate:.2f}%, 平均最高涨幅: {avg_return:.2f}%")
        else:
            print(f"[{name}] 信号数: 0")

if __name__ == "__main__":
    run_backtest()
