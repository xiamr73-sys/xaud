import ccxt
import pandas as pd
import os
import requests
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def fetch_data(symbol, timeframe='1h', limit=100):
    """
    使用 ccxt 获取指定币种的 K 线数据
    """
    print(f"正在获取 {symbol} 的 {timeframe} K 线数据...")
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # 使用合约数据
        })
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv:
            print("未获取到数据")
            return None

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def calculate_rsi(df, period=14):
    """手动计算 RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bbands(df, period=20, std_dev=2):
    """手动计算布林带"""
    mid = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = mid + (std * std_dev)
    lower = mid - (std * std_dev)
    return upper, mid, lower

def calculate_macd(df, fast=12, slow=26, signal=9):
    """手动计算 MACD"""
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_indicators(df):
    """
    计算 RSI, MACD, 布林带指标 (手动实现版本)
    """
    print("正在计算技术指标...")
    
    # 确保数据按时间排序
    df = df.sort_values('timestamp')
    
    # RSI (14)
    df['rsi'] = calculate_rsi(df)
    
    # MACD (12, 26, 9)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
    
    # Bollinger Bands (20, 2)
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = calculate_bbands(df)
    
    return df

def analyze_with_ai(symbol, df):
    """
    调用 AI API 进行行情分析
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    default_model = "gpt-4o"
    if "deepseek" in base_url:
        default_model = "deepseek-chat"
        
    model = os.getenv("OPENAI_MODEL", default_model)

    if not api_key:
        print("错误: 未找到 API Key，请在 .env 文件中配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY")
        return

    # 准备最近的数据用于分析 (取最近 5 条)
    recent_data = df.tail(5).copy()
    
    # 格式化数据字符串
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

    print(f"正在发送数据给 AI ({model})...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
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
        content = result['choices'][0]['message']['content']
        
        print("\n" + "="*30 + " AI 分析报告 " + "="*30)
        print(content)
        print("="*72 + "\n")
        
    except Exception as e:
        print(f"AI 分析请求失败: {e}")
        if 'response' in locals():
             print(f"响应内容: {response.text}")

import sys

def main():
    if len(sys.argv) > 1:
        symbol = sys.argv[1].strip().upper()
    else:
        symbol = input("请输入要分析的币种 (默认 BTC/USDT): ").strip().upper()
    
    if not symbol:
        symbol = "BTC/USDT"
    
    # 1. 获取数据
    df = fetch_data(symbol, timeframe='1h', limit=100)
    if df is None:
        return

    # 2. 计算指标
    try:
        df = calculate_indicators(df)
    except Exception as e:
        print(f"指标计算出错: {e}")
        return

    # 3. AI 分析
    analyze_with_ai(symbol, df)

if __name__ == "__main__":
    main()
