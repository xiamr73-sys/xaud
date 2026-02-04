import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import os
from datetime import datetime, timedelta

# 配置
SYMBOL = 'UAI/USDT'  # 替换为你想要分析的币种
TIMEFRAME = '1m'
LIMIT = 1440 # 获取过去 24 小时的数据 (1440 分钟)

async def fetch_data():
    exchange = ccxt.binanceusdm()
    
    print(f"正在连接 Binance Futures 获取 {SYMBOL} 数据...")
    
    try:
        # 1. 获取 1分钟 K线数据 (OHLCV)
        # 这里的 limit 是获取的数量
        print(f"正在获取 {TIMEFRAME} K线数据...")
        ohlcv = await exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=LIMIT)
        df_ohlcv = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_ohlcv['timestamp'] = pd.to_datetime(df_ohlcv['timestamp'], unit='ms')
        df_ohlcv.set_index('timestamp', inplace=True)
        
        # 2. 获取 1分钟 持仓量 (Open Interest) 历史数据
        print(f"正在获取 {TIMEFRAME} 持仓量(OI)数据...")
        # 注意: 并非所有交易所都支持细粒度的历史 OI，Binance 通常支持
        try:
            oi_history = await exchange.fetch_open_interest_history(SYMBOL, timeframe=TIMEFRAME, limit=LIMIT)
            oi_data = []
            for entry in oi_history:
                oi_data.append({
                    'timestamp': pd.to_datetime(entry['timestamp'], unit='ms'),
                    'open_interest': float(entry['openInterestAmount']),
                    'open_interest_value': float(entry['openInterestValue']) # 部分接口可能有 value
                })
            df_oi = pd.DataFrame(oi_data)
            df_oi.set_index('timestamp', inplace=True)
        except Exception as e:
            print(f"获取 OI 数据失败 (可能不支持该时间粒度): {e}")
            df_oi = pd.DataFrame()

        # 3. 获取资金费率历史
        # 资金费率通常是 8 小时一次，但我们可以获取历史记录看是否有变化
        print(f"正在获取资金费率历史数据...")
        try:
            funding_history = await exchange.fetch_funding_rate_history(SYMBOL, limit=100) # 获取最近 100 次
            funding_data = []
            for entry in funding_history:
                funding_data.append({
                    'timestamp': pd.to_datetime(entry['timestamp'], unit='ms'),
                    'funding_rate': float(entry['fundingRate'])
                })
            df_funding = pd.DataFrame(funding_data)
            if not df_funding.empty:
                df_funding.set_index('timestamp', inplace=True)
                # 资金费率是稀疏数据，我们需要将其对齐到 1分钟 K线，通常用 ffill (前向填充)
                # 但为了准确展示“何时变化”，我们先合并再处理
            else:
                print("资金费率历史为空")
        except Exception as e:
            print(f"获取资金费率历史失败: {e}")
            df_funding = pd.DataFrame()

        # 4. 数据合并
        print("正在合并数据...")
        # 以 OHLCV 为基准
        df_final = df_ohlcv.join(df_oi, how='left')
        
        # 合并资金费率
        if not df_funding.empty:
            # 因为资金费率时间点可能和 K 线不完全对齐（比如整点），我们用 merge_asof 或者重采样
            # 这里简单起见，直接 join，如果需要填充可以使用 ffill
            # 但为了看到“跳动”，我们先 join，然后决定是否 fill
            # 实际上，资金费率在未更新时是保持不变的，或者我们只关心结算时刻
            # 这里我们尝试将其 map 到最近的时间点
            df_final = df_final.join(df_funding, how='left')
            df_final['funding_rate'] = df_final['funding_rate'].ffill() # 前向填充，假设费率在下一次更新前有效
        
        # 5. 输出到 CSV
        filename = f"{SYMBOL.replace('/', '_')}_{TIMEFRAME}_data.csv"
        df_final.to_csv(filename)
        print(f"数据已成功保存到: {filename}")
        print("-" * 30)
        print("数据预览 (最后 5 行):")
        print(df_final.tail())
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(fetch_data())
