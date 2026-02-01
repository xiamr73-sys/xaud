import ccxt
import pandas as pd
import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def fetch_data_sync(symbol, timeframe='1h', limit=100):
    """
    使用 ccxt (同步模式) 获取指定币种的 K 线数据
    如果 limit > 1000，会自动分页拉取数据
    """
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        all_ohlcv = []
        # Binance limit per request is usually 1500 for futures, 1000 safe bet
        batch_limit = 1000
        
        if limit <= batch_limit:
            all_ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        else:
            # Need pagination. Strategy: Fetch from calculated start time
            # 1. Calculate duration in milliseconds
            duration_ms = exchange.parse_timeframe(timeframe) * 1000
            now = exchange.milliseconds()
            start_time = now - (limit * duration_ms)
            
            # Fetch loop
            current_since = start_time
            while len(all_ohlcv) < limit:
                # Determine how many left to fetch
                remaining = limit - len(all_ohlcv)
                fetch_limit = min(remaining, batch_limit)
                
                # Fetch
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=fetch_limit)
                
                if not ohlcv:
                    break
                    
                all_ohlcv.extend(ohlcv)
                
                # Update since for next batch (last timestamp + 1 period)
                last_timestamp = ohlcv[-1][0]
                current_since = last_timestamp + 1
                
                # Safety break if we reached current time
                if last_timestamp >= now:
                    break
        
        if not all_ohlcv:
            return None

        # Ensure we don't have duplicates and sort (though fetch_ohlcv should be sorted)
        # Convert to DF
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Remove duplicates if any
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.sort_values('timestamp')
        
        # Trim to exact limit if we got slightly more
        if len(df) > limit:
            df = df.iloc[-limit:]
            
        return df
    except Exception as e:
        print(f"Fetch data failed: {e}")
        return None

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bbands(df, period=20, std_dev=2):
    mid = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = mid + (std * std_dev)
    lower = mid - (std * std_dev)
    return upper, mid, lower

def calculate_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_indicators(df):
    df = df.sort_values('timestamp')
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = calculate_bbands(df)
    return df

def get_ai_analysis(symbol, df, api_key=None):
    """
    调用 AI API 进行行情分析，返回分析结果字符串
    """
    # 优先使用传入的 Key，否则从环境变量读取
    final_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    default_model = "gpt-4o"
    if "deepseek" in base_url:
        default_model = "deepseek-chat"
        
    model = os.getenv("OPENAI_MODEL", default_model)

    if not final_api_key:
        return "错误: 未配置 API Key。请在页面右上角输入 Key，或在 .env 文件中配置 OPENAI_API_KEY / DEEPSEEK_API_KEY。"

    recent_data = df.tail(5).copy()
    
    data_str = f"币种: {symbol}\n时间周期: 1小时\n\n最近 5 条 K 线及指标数据:\n"
    for index, row in recent_data.iterrows():
        ts = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        data_str += (
            f"时间: {ts} | 收盘价: {row['close']} | 成交量: {row['volume']}\n"
            f"  - RSI: {row['rsi']:.2f}\n"
            f"  - MACD: {row['macd']:.2f} | Signal: {row['macd_signal']:.2f} | Hist: {row['macd_hist']:.2f}\n"
            f"  - 布林带: 上轨 {row['bb_upper']:.2f} | 中轨 {row['bb_mid']:.2f} | 下轨 {row['bb_lower']:.2f}\n"
            f"--------------------------------------------------\n"
        )

    prompt = (
        f"你是一个专业的加密货币交易分析师。请根据以下 {symbol} 的最近市场数据进行分析：\n\n"
        f"{data_str}\n"
        f"请结合价格走势、成交量变化以及 RSI、MACD、布林带等技术指标，分析当前的趋势特点。\n"
        f"最后给出明确的分析结论（看涨/看跌/震荡）以及关键的支撑位和阻力位建议。"
    )
    
    headers = {
        "Authorization": f"Bearer {final_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个资深的加密货币技术分析专家，擅长通过 K 线形态和技术指标分析市场趋势。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 分析请求失败: {str(e)}"
