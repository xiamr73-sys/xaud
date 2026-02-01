import asyncio
import os
import threading
import time
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
import requests
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import ai_analysis_service  # Import the new service
import math

# Load environment variables
load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
DISCORD_WEBHOOK_GENERAL = os.getenv('DISCORD_WEBHOOK_GENERAL') or os.getenv('DISCORD_WEBHOOK_URL') # Fallback to old var
DISCORD_WEBHOOK_FIRST_ENTRY = os.getenv('DISCORD_WEBHOOK_FIRST_ENTRY')

app = Flask(__name__)

# Global cache to store analysis results
CACHE = {
    'longs': [],
    'shorts': [],
    'adx_longs': [],
    'adx_shorts': [],
    'pre_breakouts': [],
    'alert_counts': {
        'today': {}, 
        'yesterday': {}, 
        'date': None # Track current date (YYYY-MM-DD)
    },
    'discord_sent': {}, # Track last sent time for Discord alerts
    'last_updated': None,
    'is_updating': False,
    'last_top_10': set(), # Store last Top 10 symbols to detect new entries
    'seen_coins': set() # Store ALL coins seen in Top 10 to detect 'First Entry'
}

# --- Signal Backtest Storage ---
# Structure: { 'symbol_timestamp': { 'symbol': 'BTCUSDT', 'type': 'LONG', 'entry_price': 50000, 'entry_time': 1700000000, 'oi_growth': 5.5 } }
BACKTEST_SIGNALS = {} 
BACKTEST_LOCK = threading.Lock()

def send_discord_alert(content, webhook_url=None):
    # Default to General Webhook if not specified
    target_url = webhook_url or DISCORD_WEBHOOK_GENERAL
    
    if not target_url:
        print(f"错误: 未找到 Discord Webhook URL (Target: {webhook_url})")
        return
    
    payload = {"content": content}
    try:
        response = requests.post(target_url, json=payload)
        response.raise_for_status()
        print(f"Discord 推送成功 ({'General' if target_url == DISCORD_WEBHOOK_GENERAL else 'First Entry'})")
    except Exception as e:
        print(f"Discord 推送失败: {e}")

# --- Backtest Verification Logic ---
def check_backtest_results():
    """
    Periodically checks active backtest signals to see if 30 minutes have passed.
    If so, verifies the result (max ROI) and logs it.
    """
    # Note: We need a sync exchange instance or run async in thread
    # For simplicity, we'll use requests to get klines or a sync ccxt instance
    # Using a new sync ccxt instance to avoid async loop conflicts
    import ccxt as ccxt_sync
    exchange = ccxt_sync.binance({'options': {'defaultType': 'future'}})
    
    while True:
        try:
            current_time = time.time()
            signals_to_verify = []

            with BACKTEST_LOCK:
                # Find signals older than 30 minutes
                keys_to_remove = []
                for key, signal in BACKTEST_SIGNALS.items():
                    if current_time - signal['entry_time'] >= 1800: # 30 minutes = 1800 seconds
                        signals_to_verify.append(signal)
                        keys_to_remove.append(key)
                
                # Remove from active list
                for key in keys_to_remove:
                    del BACKTEST_SIGNALS[key]
            
            if signals_to_verify:
                print(f"🔍 Verifying {len(signals_to_verify)} backtest signals...")
                
                for signal in signals_to_verify:
                    symbol = signal['symbol']
                    entry_price = signal['entry_price']
                    signal_type = signal['type']
                    
                    try:
                        # Get 1m klines for the last 30 mins
                        # 30 mins * 60 sec = 1800 sec
                        # We need historical data from entry_time to entry_time + 30m
                        # CCXT fetch_ohlcv supports since
                        since_ts = int(signal['entry_time'] * 1000)
                        klines = exchange.fetch_ohlcv(symbol, '1m', since=since_ts, limit=35)
                        
                        max_price = 0
                        min_price = float('inf')
                        
                        for k in klines:
                            # k: [time, open, high, low, close, vol]
                            high = float(k[2])
                            low = float(k[3])
                            if high > max_price: max_price = high
                            if low < min_price: min_price = low
                            
                        # Calculate ROI
                        if signal_type == 'LONG':
                            if max_price > 0:
                                max_roi = ((max_price - entry_price) / entry_price) * 100
                                result_emoji = "✅" if max_roi > 0.5 else "❌"
                            else:
                                max_roi = 0
                                result_emoji = "❓"
                        else: # SHORT
                            if min_price < float('inf'):
                                max_roi = ((entry_price - min_price) / entry_price) * 100
                                result_emoji = "✅" if max_roi > 0.5 else "❌"
                            else:
                                max_roi = 0
                                result_emoji = "❓"

                        # Log result
                        log_msg = (
                            f"📉 **信号回测报告**\n"
                            f"币种: {symbol} | 方向: {signal_type}\n"
                            f"入场价: {entry_price} | OI增长: {signal['oi_growth']:.2f}%\n"
                            f"30分钟内最大涨幅: {max_roi:.2f}% {result_emoji}"
                        )
                        print(f"Backtest Result: {symbol} {max_roi:.2f}%")
                        send_discord_alert(log_msg, webhook_url=DISCORD_WEBHOOK_GENERAL)
                        
                    except Exception as e:
                        print(f"Error verifying signal for {symbol}: {e}")
                        
        except Exception as e:
            print(f"Backtest verification loop error: {e}")
        
        time.sleep(60) # Check every minute

# Start background thread for backtest verification
threading.Thread(target=check_backtest_results, daemon=True).start()

def calculate_rsi(df, period=14):
    if len(df) < period + 1:
        return pd.Series(index=df.index, dtype=float)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df['rsi']

def calculate_bbands(df, period=20, std_dev=2):
    if len(df) < period:
        return None, None, None
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * std_dev)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * std_dev)
    
    # Calculate Band Width
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    return df['bb_upper'], df['bb_mid'], df['bb_lower']

def calculate_adx(df, period=14):
    if len(df) < period + 1:
        return pd.Series(index=df.index, dtype=float)
        
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0.0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0.0)
    
    alpha = 1 / period
    
    df['tr_smooth'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
    df['plus_dm_smooth'] = df['plus_dm'].ewm(alpha=alpha, adjust=False).mean()
    df['minus_dm_smooth'] = df['minus_dm'].ewm(alpha=alpha, adjust=False).mean()
    
    df['plus_di'] = 100 * (df['plus_dm_smooth'] / df['tr_smooth'])
    df['minus_di'] = 100 * (df['minus_dm_smooth'] / df['tr_smooth'])
    
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()
    
    return df['adx']

def calculate_atr(df, period=14):
    if len(df) < period + 1:
        return pd.Series(index=df.index, dtype=float)
        
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    # Simple Moving Average for ATR as per standard, or EMA. Wilder used RMA (Running MA).
    # Using Rolling Mean for simplicity or ewm with alpha=1/period (RMA approximation)
    df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
    return df['atr']

def analyze_trend(symbol, ohlcv_15m, ohlcv_1h=None):
    if not ohlcv_15m or len(ohlcv_15m) < 60:
        return None
        
    # 15m Analysis
    df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
    df['adx'] = calculate_adx(df, 14)
    df['atr'] = calculate_atr(df, 14)
    df['rsi'] = calculate_rsi(df, 14)
    calculate_bbands(df, 20, 2)
    df['vol_ma20'] = df['volume'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    close = latest['close']
    open_price = latest['open']
    ema20 = latest['ema20']
    ema60 = latest['ema60']
    adx = latest['adx']
    atr = latest['atr']
    rsi = latest['rsi']
    volume = latest['volume']
    vol_ma20 = latest['vol_ma20']
    
    # Pre-breakout Analysis Variables
    bb_width = latest.get('bb_width', 0)
    
    if vol_ma20 > 0:
        vol_multiplier = volume / vol_ma20
    else:
        vol_multiplier = 0
        
    result = {
        'symbol': symbol,
        'close': close,
        'adx': adx,
        'rsi': rsi,
        'bb_width': bb_width,
        'vol_multiplier': vol_multiplier,
        'trend': 'NEUTRAL',
        'open_interest_change': 0.0,
        'institutional_entry': False,
        'funding_rate': 0.0,
        'poc_signal': False,
        'funding_signal': None, 
        'oi_signal': None,
        'mtf_confirmed': False,
        'atr_volatility': False,
        'order_flow_signal': False,
        'pre_breakout_score': 0,
        'pre_breakout_reasons': []
    }
    
    # --- Pre-breakout Logic ---
    reasons = []
    score = 0
    
    # 1. Squeeze Identification: BB Width near 24h low
    # We fetch 100 candles of 15m (~25 hours). perfect.
    if 'bb_width' in df.columns:
        # Check last 96 candles (24h)
        recent_widths = df['bb_width'].iloc[-96:]
        min_width = recent_widths.min()
        if bb_width <= min_width * 1.1: # Within 10% of 24h low
            score += 40
            reasons.append('BB Squeeze')
            
    # 2. Volume/Price Divergence
    # Price sideways (< 0.5% change)
    # 15m change: abs(close - open) / open
    price_change_pct = abs(close - open_price) / open_price
    if price_change_pct < 0.005:
        # Check Volume Spike (Current > 1.5x Avg or similar, prompt said "Volume increase > 3%" which is tiny for volume.
        # Assuming "Volume > Previous Volume * 1.03" and "OI > Previous OI * 1.03"
        # Since we calculate OI Change later, we mark a flag here for Price Sideways
        # and check OI later.
        pass # Will check combined logic after OI is populated
        
    # 3. RSI Bottom Lift
    # Price < EMA20 (Not broken yet)
    # RSI from oversold (<30 or <40) and rising for 3 candles
    if close < ema20:
        if len(df) >= 3:
            rsi_3 = df['rsi'].iloc[-3]
            rsi_2 = df['rsi'].iloc[-2]
            rsi_1 = df['rsi'].iloc[-1]
            
            if rsi_3 < 40 and rsi_1 > rsi_2 > rsi_3:
                score += 30
                reasons.append('RSI Lift')
                
    result['pre_breakout_reasons'] = reasons
    result['pre_breakout_base_score'] = score # To be added with OI score later
    
    # ATR Volatility Filter: Current Candle Range > 1.5 * ATR (or recent movement)
    
    if len(df) >= 3:
        recent_high = df['high'].iloc[-3:].max()
        recent_low = df['low'].iloc[-3:].min()
        recent_range = recent_high - recent_low
        if recent_range > 1.5 * atr:
            result['atr_volatility'] = True
    
    # Order Flow Approximation
    if vol_multiplier > 3.0:
        result['order_flow_signal'] = True

    # 1H Trend Analysis (Higher Timeframe Filter)
    htf_trend_bullish = False
    htf_trend_bearish = False
    
    if ohlcv_1h and len(ohlcv_1h) >= 20:
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema20'] = df_1h['close'].ewm(span=20, adjust=False).mean()
        latest_1h = df_1h.iloc[-1]
        
        # Bullish: Close > EMA20
        if latest_1h['close'] > latest_1h['ema20']:
            htf_trend_bullish = True
        # Bearish: Close < EMA20
        elif latest_1h['close'] < latest_1h['ema20']:
            htf_trend_bearish = True
            
    # Calculate POC Approximation (Volume Profile)
    if len(ohlcv_15m) >= 20:
        recent_candles = ohlcv_15m[-20:]
        max_vol_candle = max(recent_candles, key=lambda x: x[5]) 
        max_vol_price = max_vol_candle[4] 
        if close > max_vol_price:
            result['poc_signal'] = True
            
    # Calculate Trend Score
    oi_score = max(result['open_interest_change'], 0) * 10
    vol_score = result['vol_multiplier'] * 10
    
    trend_score = (adx * 0.4) + (vol_score * 0.3) + (oi_score * 0.3)
    result['trend_score'] = trend_score
    result['atr'] = atr
    
    # Determine Trend with MTF & ATR Filter
    # Only trigger if ATR volatility is present
    if result['atr_volatility']:
        # Strong Long: 15m (Close > EMA20 > EMA60 & ADX > 25) AND 1H (Close > EMA20)
        if close > ema20 > ema60 and adx > 25:
            if htf_trend_bullish:
                result['trend'] = 'STRONG_LONG'
                result['mtf_confirmed'] = True
            else:
                result['trend'] = 'STRONG_LONG'
                
        # Strong Short: 15m (Close < EMA20 < EMA60 & ADX > 25) AND 1H (Close < EMA20)
        elif close < ema20 < ema60 and adx > 25:
            if htf_trend_bearish:
                result['trend'] = 'STRONG_SHORT'
                result['mtf_confirmed'] = True
            else:
                result['trend'] = 'STRONG_SHORT'
    else:
        # If volatility is too low, force NEUTRAL even if EMAs match
        result['trend'] = 'NEUTRAL'

    # Calculate Dynamic ATR TP/SL (AFTER Trend is determined)
    
    n_atr = 2.0
    m_atr = 4.0
    
    # Assuming 'close' is the entry price for signal
    if result['trend'] == 'STRONG_LONG':
        result['sl_price'] = close - (n_atr * atr)
        result['tp_price'] = close + (m_atr * atr)
    elif result['trend'] == 'STRONG_SHORT':
        result['sl_price'] = close + (n_atr * atr)
        result['tp_price'] = close - (m_atr * atr)
    else:
        result['sl_price'] = 0.0
        result['tp_price'] = 0.0
        
    return result

async def fetch_candles(exchange, symbol, timeframe='15m', limit=100):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return symbol, ohlcv
    except Exception as e:
        return symbol, []

async def fetch_open_interest_history(exchange, symbol):
    try:
        oi_history = await exchange.fetch_open_interest_history(symbol, timeframe='5m', limit=2)
        return symbol, oi_history
    except Exception as e:
        return symbol, []

async def fetch_funding_rate(exchange, symbol):
    try:
        funding = await exchange.fetch_funding_rate(symbol)
        return symbol, funding
    except Exception as e:
        return symbol, None

async def update_data():
    global CACHE
    CACHE['is_updating'] = True
    print("Starting data update...")
    
    exchange_config = {
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    }
    if API_KEY and 'your_api_key' not in API_KEY:
        exchange_config['apiKey'] = API_KEY
        exchange_config['secret'] = SECRET_KEY
    
    exchange = ccxt.binance(exchange_config)
    
    try:
        tickers = await exchange.fetch_tickers()
        usdt_pairs = []
        for symbol, ticker in tickers.items():
            if '/USDT' in symbol and ticker.get('quoteVolume'):
                usdt_pairs.append(ticker)
        
        sorted_pairs = sorted(usdt_pairs, key=lambda x: x['quoteVolume'], reverse=True)
        top_n = sorted_pairs[:300]
        
        tasks_ohlcv = []
        tasks_ohlcv_1h = []
        tasks_oi = []
        tasks_funding = []
        
        for pair in top_n:
            symbol = pair['symbol']
            tasks_ohlcv.append(fetch_candles(exchange, symbol, '15m'))
            tasks_ohlcv_1h.append(fetch_candles(exchange, symbol, '1h', limit=50))
            tasks_oi.append(fetch_open_interest_history(exchange, symbol))
            tasks_funding.append(fetch_funding_rate(exchange, symbol))
            
        results_ohlcv = await asyncio.gather(*tasks_ohlcv)
        results_ohlcv_1h = await asyncio.gather(*tasks_ohlcv_1h)
        results_oi = await asyncio.gather(*tasks_oi)
        results_funding = await asyncio.gather(*tasks_funding)
        
        ohlcv_1h_data = {symbol: data for symbol, data in results_ohlcv_1h}
        oi_data = {symbol: history for symbol, history in results_oi}
        funding_data = {symbol: data for symbol, data in results_funding}
        
        longs = []
        shorts = []
        pre_breakouts_list = []
        
        for symbol, ohlcv in results_ohlcv:
            ohlcv_1h = ohlcv_1h_data.get(symbol, [])
            analysis = analyze_trend(symbol, ohlcv, ohlcv_1h)
            if analysis:
                # OI Analysis
                oi_history = oi_data.get(symbol, [])
                if len(oi_history) >= 2:
                    current_oi = oi_history[-1]['openInterestAmount']
                    prev_oi = oi_history[-2]['openInterestAmount']
                    if prev_oi and prev_oi > 0:
                        analysis['open_interest_change'] = ((current_oi - prev_oi) / prev_oi) * 100
                    
                    # Institutional Entry Check
                    if analysis['open_interest_change'] > 0.1:
                         if len(ohlcv) >= 2:
                            current_close = ohlcv[-1][4]
                            prev_close = ohlcv[-2][4]
                            if current_close != prev_close:
                                analysis['institutional_entry'] = True
                                
                # Funding Rate Analysis
                funding_info = funding_data.get(symbol)
                if funding_info:
                    fr = funding_info.get('fundingRate', 0)
                    analysis['funding_rate'] = fr
                    
                    if analysis['trend'] == 'STRONG_LONG' and fr < 0.0001:
                        analysis['funding_signal'] = 'BULLISH_DIVERGENCE'
                    
                    if analysis['trend'] == 'STRONG_LONG' and fr > 0.001:
                        analysis['funding_signal'] = 'EXTREME_GREED'
                        
                # OI Signal Logic
                is_breakout = analysis['trend'] != 'NEUTRAL' or analysis['poc_signal']
                
                if is_breakout:
                    if analysis['open_interest_change'] > 0.5: 
                        analysis['oi_signal'] = 'TRUE_BREAKOUT'
                    elif analysis['open_interest_change'] < -0.1: 
                        analysis['oi_signal'] = 'FAKE_BREAKOUT'

                # --- Complete Pre-breakout Analysis ---
                pb_score = analysis.get('pre_breakout_base_score', 0)
                reasons = analysis.get('pre_breakout_reasons', [])
                
                # Vol/Price Divergence
                if analysis['trend'] == 'NEUTRAL':
                    if analysis['open_interest_change'] > 3.0:
                         if analysis['vol_multiplier'] > 1.2:
                             pb_score += 50
                             reasons.append('Vol/OI Div')
                
                # Squeeze + OI Increase
                if 'BB Squeeze' in reasons and analysis['open_interest_change'] > 0.5:
                    pb_score += 20
                    reasons.append('Squeeze+OI')
                    
                analysis['pre_breakout_score'] = pb_score
                analysis['pre_breakout_reasons'] = reasons
                
                if pb_score >= 40:
                    analysis['is_pre_breakout'] = True
                    pre_breakouts_list.append(analysis)
                    
                    # Increment Alert Count
                    if 'alert_counts' not in CACHE:
                        CACHE['alert_counts'] = {}
                    
                    current_count = CACHE['alert_counts'].get(symbol, 0) + 1
                    CACHE['alert_counts'][symbol] = current_count
                    
                    analysis['alert_count_today'] = current_count
                    analysis['alert_count_yesterday'] = CACHE['alert_counts'].get('yesterday', {}).get(symbol, 0)
                    # Legacy field for alerts.html
                    analysis['alert_count'] = current_count 
                else:
                    analysis['is_pre_breakout'] = False

                # Classify Trend
                if analysis['trend'] == 'STRONG_LONG':
                    longs.append(analysis)
                elif analysis['trend'] == 'STRONG_SHORT':
                    shorts.append(analysis)
                
        # Sort by Trend Score (Descending) and Keep Top 3
        CACHE['longs'] = sorted(longs, key=lambda x: x.get('trend_score', 0), reverse=True)[:3]
        CACHE['shorts'] = sorted(shorts, key=lambda x: x.get('trend_score', 0), reverse=True)[:3]

        # Sort by ADX (Descending) and Keep Top 3
        longs_sorted = sorted(CACHE['longs'], key=lambda x: x.get('adx', 0), reverse=True)[:3]
        shorts_sorted = sorted(CACHE['shorts'], key=lambda x: x.get('adx', 0), reverse=True)[:3]
        
        CACHE['adx_longs'] = longs_sorted
        CACHE['adx_shorts'] = shorts_sorted

        # --- BTC Trend Filter Logic ---
        btc_trend = "NEUTRAL"
        try:
            # Fetch BTC 5m klines for trend analysis
            btc_klines = await exchange.fetch_ohlcv('BTC/USDT', '5m', limit=20)
            
            if btc_klines:
                btc_df = pd.DataFrame(btc_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Calculate Indicators
                btc_adx = calculate_adx(btc_df, 14)
                btc_df['ema_fast'] = btc_df['close'].ewm(span=9, adjust=False).mean()
                btc_df['ema_slow'] = btc_df['close'].ewm(span=21, adjust=False).mean()
                
                current_adx = btc_adx.iloc[-1]
                current_fast = btc_df['ema_fast'].iloc[-1]
                current_slow = btc_df['ema_slow'].iloc[-1]
                
                # Define "Sharp Rise/Fall"
                # Condition: High ADX (>25) AND Clear EMA Separation
                if current_adx > 25:
                    if current_fast > current_slow:
                        btc_trend = "UP"
                    elif current_fast < current_slow:
                        btc_trend = "DOWN"
                
                print(f"BTC Trend: {btc_trend} (ADX: {current_adx:.2f})")
            
        except Exception as e:
            print(f"Error analyzing BTC trend: {e}")
        # ------------------------------

        # --- New Top 10 Entry Detection ---
        all_signals = longs + shorts
        top_10_list = sorted(all_signals, key=lambda x: x.get('trend_score', 0), reverse=True)[:10]
        current_top_10_symbols = {item['symbol'] for item in top_10_list}
        
        # Check for new entries
        if CACHE.get('last_top_10'): # Skip first run
            new_entries = current_top_10_symbols - CACHE['last_top_10']
            
            if new_entries:
                new_entry_msg = []
                first_entry_msg = []
                for symbol in new_entries:
                    # Find the item data
                    item = next((x for x in top_10_list if x['symbol'] == symbol), None)
                    if item:
                        signal_icon = "🟢" if item['trend'] == 'STRONG_LONG' else "🔴"
                        signal_text = "LONG" if item['trend'] == 'STRONG_LONG' else "SHORT"
                        
                        if symbol not in CACHE['seen_coins']:
                            CACHE['seen_coins'].add(symbol)
                            first_entry_msg.append(f"✨ **发现新星**: {symbol} | 信号: {signal_icon} {signal_text} | 价格: {item['close']}")
                        else:
                            new_entry_msg.append(f"🚀 **新进榜单**: {symbol} | 信号: {signal_icon} {signal_text} | 价格: {item['close']}")
                
                # Send 'First Entry' Alert to Dedicated Channel
                if first_entry_msg:
                    alert_content = "\n".join(first_entry_msg)
                    if DISCORD_WEBHOOK_FIRST_ENTRY:
                        send_discord_alert(alert_content, webhook_url=DISCORD_WEBHOOK_FIRST_ENTRY)
                    else:
                        print("Warning: First Entry Webhook not set, falling back to General")
                        send_discord_alert(alert_content, webhook_url=DISCORD_WEBHOOK_GENERAL)

                # Send Regular 'New Entry' Alert to General Channel
                if new_entry_msg:
                    alert_content = "**🔔 Top 10 榜单变动**\n" + "\n".join(new_entry_msg)
                    send_discord_alert(alert_content)
        
        # Update Cache
        CACHE['last_top_10'] = current_top_10_symbols
        # -----------------------------------

        # --- Send Discord Summary Report ---
        discord_report = []
        
        # Process Longs (Only if BTC is NOT crashing)
        if btc_trend != "DOWN":
            for item in CACHE['longs']: # Use sorted Top 3 Longs
                symbol = item['symbol']
                # Track alert to prevent spamming (limit 1 per hour per coin)
                last_sent = CACHE['discord_sent'].get(symbol, 0)
                if time.time() - last_sent > 3600:
                    icon = "🟢"
                    discord_report.append(f"{icon} **{symbol}** | Price: {item['close']} | Score: {item.get('trend_score', 0):.1f}")
                    CACHE['discord_sent'][symbol] = time.time()
                    
                    # --- Record for Backtest ---
                    with BACKTEST_LOCK:
                        signal_id = f"{symbol}_{int(time.time())}"
                        BACKTEST_SIGNALS[signal_id] = {
                            'symbol': symbol,
                            'type': 'LONG',
                            'entry_price': float(item['close']),
                            'entry_time': time.time(),
                            'oi_growth': float(item['open_interest_change'])
                        }
                    # ---------------------------
        else:
            print("BTC is dumping! Suppressing LONG alerts.")

        # Process Shorts (Only if BTC is NOT mooning)
        if btc_trend != "UP":
            for item in CACHE['shorts']: # Use sorted Top 3 Shorts
                symbol = item['symbol']
                last_sent = CACHE['discord_sent'].get(symbol, 0)
                if time.time() - last_sent > 3600:
                    icon = "🔴"
                    discord_report.append(f"{icon} **{symbol}** | Price: {item['close']} | Score: {item.get('trend_score', 0):.1f}")
                    CACHE['discord_sent'][symbol] = time.time()

                    # --- Record for Backtest ---
                    with BACKTEST_LOCK:
                        signal_id = f"{symbol}_{int(time.time())}"
                        BACKTEST_SIGNALS[signal_id] = {
                            'symbol': symbol,
                            'type': 'SHORT',
                            'entry_price': float(item['close']),
                            'entry_time': time.time(),
                            'oi_growth': float(item['open_interest_change'])
                        }
                    # ---------------------------
        else:
            print("BTC is pumping! Suppressing SHORT alerts.")

        # Process High ADX Signals (Apply same BTC filter)
        # We need to iterate over ADX lists
        for item in CACHE['adx_longs']:
            symbol = item['symbol']
            if btc_trend == "DOWN": continue
            
            last_sent = CACHE['discord_sent'].get(symbol, 0)
            if time.time() - last_sent > 3600:
                icon = "🔥" 
                discord_report.append(f"{icon} **{symbol}** (High ADX) | Trend: {item['trend']} | Price: {item['close']}")
                CACHE['discord_sent'][symbol] = time.time()

                with BACKTEST_LOCK:
                    signal_id = f"{symbol}_{int(time.time())}"
                    BACKTEST_SIGNALS[signal_id] = {
                        'symbol': symbol,
                        'type': 'LONG',
                        'entry_price': float(item['close']),
                        'entry_time': time.time(),
                        'oi_growth': float(item['open_interest_change'])
                    }
        
        for item in CACHE['adx_shorts']:
            symbol = item['symbol']
            if btc_trend == "UP": continue
            
            last_sent = CACHE['discord_sent'].get(symbol, 0)
            if time.time() - last_sent > 3600:
                icon = "❄️" 
                discord_report.append(f"{icon} **{symbol}** (High ADX) | Trend: {item['trend']} | Price: {item['close']}")
                CACHE['discord_sent'][symbol] = time.time()

                with BACKTEST_LOCK:
                    signal_id = f"{symbol}_{int(time.time())}"
                    BACKTEST_SIGNALS[signal_id] = {
                        'symbol': symbol,
                        'type': 'SHORT',
                        'entry_price': float(item['close']),
                        'entry_time': time.time(),
                        'oi_growth': float(item['open_interest_change'])
                    }
                
        # Only send if there are reports
        if discord_report:
            summary_msg = "\n".join(discord_report)
            summary_msg = f"📊 **Market Update ({time.strftime('%H:%M:%S')})**\n{summary_msg}"
            send_discord_alert(summary_msg, webhook_url=DISCORD_WEBHOOK_GENERAL)
        # -----------------------------------
        
        # Sort Pre-breakouts
        CACHE['pre_breakouts'] = sorted(pre_breakouts_list, key=lambda x: x.get('pre_breakout_score', 0), reverse=True)
        
        # Store raw timestamp for easier calculation
        CACHE['last_updated_ts'] = time.time()
        CACHE['last_updated'] = time.strftime('%H:%M:%S')
        print(f"Data updated. Longs: {len(longs)}, Shorts: {len(shorts)}")
        
    except Exception as e:
        print(f"Update failed: {e}")
    finally:
        await exchange.close()
        CACHE['is_updating'] = False

@app.route('/')
def index():
    # Force UTF-8 encoding for the response
    response = app.make_response(render_template('monitor_dashboard.html'))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/alerts')
def alerts_page():
    # Force UTF-8 encoding for the response
    response = app.make_response(render_template('alerts.html'))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/ai-analysis')
def ai_analysis_page():
    # Force UTF-8 encoding for the response
    response = app.make_response(render_template('ai_analysis.html'))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/api/analyze', methods=['POST'])
def analyze_crypto():
    data = request.get_json()
    symbol = data.get('symbol', 'BTC/USDT').strip().upper()
    api_key = data.get('api_key')  # Get API Key from request
    
    # 1. Fetch Data
    # Updated to fetch 2300 candles as requested for deeper analysis
    df = ai_analysis_service.fetch_data_sync(symbol, limit=2300)
    if df is None:
        return jsonify({'success': False, 'message': f'Failed to fetch data for {symbol}'})
        
    # 2. Calculate Indicators
    try:
        df = ai_analysis_service.calculate_indicators(df)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Indicator calculation error: {str(e)}'})
        
    # 3. AI Analysis
    analysis_result = ai_analysis_service.get_ai_analysis(symbol, df, api_key=api_key)
    
    return jsonify({
        'success': True, 
        'symbol': symbol,
        'analysis': analysis_result
    })

def clean_nan(obj):
    """
    Recursively replace NaN/Infinity with None (which becomes null in JSON)
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj

@app.route('/api/data')
def get_data():
    # Ensure JSON response is UTF-8 and clean of NaNs
    # Filter out set objects (like last_top_10) which are not JSON serializable
    filtered_cache = {k: v for k, v in CACHE.items() if not isinstance(v, set)}
    cleaned_cache = clean_nan(filtered_cache)
    response = jsonify(cleaned_cache)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/api/test_first_entry')
def test_first_entry():
    """
    Simulate a 'First Entry' event to verify Discord First Entry Webhook.
    """
    if not DISCORD_WEBHOOK_FIRST_ENTRY:
        return jsonify({'status': 'error', 'message': 'First Entry Webhook not configured'}), 400
        
    fake_symbol = "TEST-COIN"
    fake_price = 123.45
    msg = f"✨ **[TEST] 发现新潜力股！** {fake_symbol} 首次杀入前十 | 信号: 🟢 LONG | 价格: {fake_price}"
    
    try:
        send_discord_alert(msg, webhook_url=DISCORD_WEBHOOK_FIRST_ENTRY)
        return jsonify({'status': 'success', 'message': 'Test alert sent to First Entry Webhook'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/refresh', methods=['POST', 'GET'])
def refresh_data():
    # Trigger manual update in background thread (Non-blocking)
    if not CACHE['is_updating']:
        thread = threading.Thread(target=lambda: asyncio.run(update_data()))
        thread.start()
        return jsonify({'status': 'started', 'message': 'Background update started'})
    return jsonify({'status': 'busy', 'message': 'Update already in progress'})

def background_task():
    """
    Background loop to update data every 5 minutes.
    Designed for Google Cloud Run with --no-cpu-throttling.
    """
    while True:
        print("Running automatic background update...")
        try:
            asyncio.run(update_data())
        except Exception as e:
            print(f"Background update error: {e}")
        # Update every 5 minutes (300 seconds)
        time.sleep(300)

if __name__ == '__main__':
    # Start background thread for automatic updates
    # This works perfectly on Google Cloud Run with CPU allocation enabled
    t = threading.Thread(target=background_task)
    t.daemon = True
    t.start()
    
    # Send startup notification
    print(f"DEBUG: General Webhook configured: {bool(DISCORD_WEBHOOK_GENERAL)}")
    if DISCORD_WEBHOOK_GENERAL:
        print(f"DEBUG: General Webhook starts with: {DISCORD_WEBHOOK_GENERAL[:30]}...")
    
    print(f"DEBUG: First Entry Webhook configured: {bool(DISCORD_WEBHOOK_FIRST_ENTRY)}")
    if DISCORD_WEBHOOK_FIRST_ENTRY:
        print(f"DEBUG: First Entry Webhook starts with: {DISCORD_WEBHOOK_FIRST_ENTRY[:30]}...")

    if DISCORD_WEBHOOK_GENERAL:
        try:
            print("Sending startup notification to Discord (General)...")
            send_discord_alert("🟢 **Crypto Monitor Bot Started**\nReady to track market trends!", webhook_url=DISCORD_WEBHOOK_GENERAL)
        except Exception as e:
            print(f"Failed to send startup notification: {e}")
    
    # Default port should be 5001 if not set, but Cloud Run passes PORT env var
    # If locally running without PORT set, default to 5001 to match user preference
    port = int(os.environ.get('PORT', 5001)) 
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)