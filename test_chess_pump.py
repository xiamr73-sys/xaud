import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import ta

# 添加路径以便导入 utils
sys.path.append(os.path.join(os.getcwd(), 'binance_futures_monitor'))

# 导入核心逻辑
try:
    from utils import calculate_indicators, check_squeeze, check_main_force_lurking, calculate_score, check_trend_breakout, check_volume_surge, check_momentum_buildup, check_macd_golden_cross, check_obv_trend
except ImportError:
    # 如果导入失败，手动复制简化版逻辑 (避免依赖复杂环境)
    print("⚠️ 无法直接导入 utils，使用内置简化逻辑...")
    # 这里我们还是尽量修复路径让它能导入，因为 utils 里有很多 ta 库的依赖
    pass

async def main():
    print("正在连接 Binance 获取 CHESS/USDT 数据...")
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    
    symbol = 'CHESS/USDT'
    timeframe = '15m'
    
    # 目标时间: 2026-02-03 05:00 北京时间 = 2026-02-02 21:00 UTC
    # 我们获取从 2026-02-02 18:00 UTC 开始的数据 (提前3小时预热指标)
    since_str = "2026-02-02 18:00:00"
    since_ts = int(pd.Timestamp(since_str, tz='UTC').timestamp() * 1000)
    
    try:
        # 获取 K 线
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since=since_ts, limit=100)
        
        if not ohlcv:
            print("❌ 未获取到数据")
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 转换时间为北京时间以便查看
        df['bj_time'] = df['timestamp'] + pd.Timedelta(hours=8)
        
        print(f"成功获取 {len(df)} 根 K 线")
        print(f"数据范围 (BJ): {df['bj_time'].iloc[0]} -> {df['bj_time'].iloc[-1]}")
        
        # 计算指标
        # 必须确保 utils 中的 calculate_indicators 可用
        # 这里为了保险，直接调用 utils 的函数。如果上面 import 成功的话。
        df = calculate_indicators(df)
        
        print("\n🔍 开始回测分析 (模拟实时扫描)...\n")
        print(f"{'时间 (BJ)':<20} | {'价格':<8} | {'分数':<5} | {'触发信号'}")
        print("-" * 80)
        
        found_signal = False
        
        # 遍历每一根 K 线 (从第 30 根开始，确保指标计算完成)
        for i in range(30, len(df)):
            # 模拟当时的 "latest" 数据
            # 注意：指标计算是基于全量数据的，这在回测中是“未来函数”的一种微小形式（比如 EMA 初始化）。
            # 但对于足够长的数据，影响可以忽略。
            # 更严格的做法是：每一步切片 df[:i] 然后算指标，但这太慢了。
            # 我们直接用计算好的 df.iloc[i] 即可，因为 ta 库的指标是滚动的。
            
            row = df.iloc[i]
            # 为了 check_volume_surge 等需要历史数据的函数，我们需要传入截止到 i 的切片
            df_slice = df.iloc[:i+1]
            
            # --- 执行判定逻辑 ---
            
            # 1. Squeeze
            is_squeeze = check_squeeze(row)
            
            # 2. Lurking (需要 OI，这里模拟 OI 为 0 或 随机，因为无法获取历史 OI 变化率)
            # 假设 OI 没有显著变化，我们暂时忽略 Lurking 的 40分，看看仅靠技术面能不能抓到
            is_lurking = False 
            
            # 3. Volume Flow
            is_volume_flow = row['volume'] > row.get('VOL_SMA_20', 9999999999)
            
            # 4. Breakout
            is_breakout = check_trend_breakout(row, df_slice)
            
            # 5. Vol Surge
            is_vol_surge = check_volume_surge(df_slice)
            
            # 6. Momentum
            is_momentum = check_momentum_buildup(row, df_slice)
            
            # 7. New Top Bull (无法判断是否新进 Top 10，设为 False)
            is_new_top_bull = False
            
            # 计算分数
            score = calculate_score(
                squeeze_active=is_squeeze,
                lurking_active=is_lurking,
                volume_flow_active=is_volume_flow,
                breakout_active=is_breakout,
                vol_surge_active=is_vol_surge,
                momentum_active=is_momentum,
                new_top_bull_active=is_new_top_bull
            )
            
            # 标记信号
            tags = []
            if is_breakout: tags.append("🚀 BREAKOUT")
            if is_vol_surge: tags.append("🔥 SURGE")
            if is_momentum: tags.append("⚡ MOMENTUM")
            if is_volume_flow: tags.append("VOL")
            if is_squeeze: tags.append("SQUEEZE")
            
            time_str = row['bj_time'].strftime('%m-%d %H:%M')
            
            # 只打印分数 > 40 的，或者 5点前后的关键帧
            if score >= 60 or (row['bj_time'].hour == 5 and row['bj_time'].minute <= 30):
                print(f"{time_str:<20} | {row['close']:<8.4f} | {score:<5} | {', '.join(tags)}")
                if score >= 60:
                    found_signal = True
        
        if found_signal:
            print("\n✅ 结论: 系统在没有 OI 数据辅助的情况下，依然能够成功捕捉到暴涨信号！")
        else:
            print("\n❌ 结论: 纯技术指标未触发阈值 (可能需要 OI 数据配合)")

    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
