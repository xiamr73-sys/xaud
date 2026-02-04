import pandas as pd
import ta
import numpy as np

class StrategyEngine:
    """
    量化策略引擎 (Strategy Engine)
    负责计算技术指标并根据预设逻辑生成交易信号。
    """
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        """
        计算技术指标 (Indicators Calculation)
        包括 ATR, Bollinger Bands, RSI, EMA, MACD, VWAP
        """
        if df.empty:
            return df
        
        # 确保有足够的数据
        
        # 1. ATR (14) - 用于止损计算 (Average True Range)
        atr_indicator = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ATR'] = atr_indicator.average_true_range()
        
        # 2. 布林带 (20, 2) - 用于均值回归策略 (Bollinger Bands)
        bb_indicator = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_High'] = bb_indicator.bollinger_hband()
        df['BB_Low'] = bb_indicator.bollinger_lband()
        
        # 3. RSI (14) - 相对强弱指标 (Relative Strength Index)
        rsi_indicator = ta.momentum.RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi_indicator.rsi()
        
        # 4. EMA 20, 50 - 指数移动平均线 (Exponential Moving Average)
        df['EMA_20'] = ta.trend.EMAIndicator(close=df['Close'], window=20).ema_indicator()
        df['EMA_50'] = ta.trend.EMAIndicator(close=df['Close'], window=50).ema_indicator()
        
        # 5. MACD -异同移动平均线 (Moving Average Convergence Divergence)
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        
        # 6. VWAP - 成交量加权平均价 (Volume Weighted Average Price)
        vwap = ta.volume.VolumeWeightedAveragePrice(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])
        df['VWAP'] = vwap.volume_weighted_average_price()
        
        return df

    def calculate_pivots(self, df):
        """
        计算枢轴点 (Pivot Points)
        使用前一日的 High, Low, Close 计算 Pivot, R1, S1
        """
        # 简化处理：使用上一根K线的 HLC 来推算当前的支撑阻力位
        # Standard: Pivot = (H + L + C) / 3
        # R1 = 2*PP - L
        # S1 = 2*PP - H
        
        df['PP'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
        df['R1'] = 2 * df['PP'] - df['Low'].shift(1)
        df['S1'] = 2 * df['PP'] - df['High'].shift(1)
        return df

    def check_signal(self, symbol, df):
        """
        核心策略逻辑检查 (Signal Generation)
        根据品种应用特定的策略逻辑。
        """
        if df.empty or len(df) < 50:
            return {'signal': 'WAIT', 'reason': '数据不足 (Not enough data)'}
            
        df = self.calculate_indicators(df)
        df = self.calculate_pivots(df)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] # 用于检查交叉信号 (Crossover check)
        
        signal = 'WAIT'
        reason = ''
        entry_price = last_row['Close']
        sl = 0.0
        tp = 0.0
        
        # ---------------------------------------------------------
        # 1. XAUUSD (黄金) & XAGUSD (白银) —— [均值回归策略]
        # 逻辑：当价格跌破下轨且 RSI < 30 时做多；触及上轨且 RSI > 70 时做空。
        # ---------------------------------------------------------
        if symbol in ['XAUUSD', 'XAGUSD']:
            # 做多信号 (Long Signal)
            if last_row['Close'] < last_row['BB_Low'] and last_row['RSI'] < 30:
                signal = 'BUY'
                reason = '均值回归: 价格跌破布林下轨 & RSI < 30'
            # 做空信号 (Short Signal)
            elif last_row['Close'] > last_row['BB_High'] and last_row['RSI'] > 70:
                signal = 'SELL'
                reason = '均值回归: 价格突破布林上轨 & RSI > 70'
                
        # ---------------------------------------------------------
        # 2. NAS100 (纳指) —— [动量趋势追踪策略]
        # 逻辑：当 EMA 20 上穿 50 且 MACD 柱状图为正时，视为强趋势买入信号。
        # ---------------------------------------------------------
        elif symbol == 'NAS100':
            # 检查金叉 (Golden Cross): 上一根 EMA20 <= EMA50, 当前 EMA20 > EMA50
            cross_up = prev_row['EMA_20'] <= prev_row['EMA_50'] and last_row['EMA_20'] > last_row['EMA_50']
            
            # 做多信号 (Long Signal)
            if cross_up and last_row['MACD_Hist'] > 0:
                signal = 'BUY'
                reason = '动量趋势: EMA20 金叉 EMA50 & MACD > 0'
            # (可选) 做空信号 logic for symmetry (Optional Short)
            elif prev_row['EMA_20'] >= prev_row['EMA_50'] and last_row['EMA_20'] < last_row['EMA_50'] and last_row['MACD_Hist'] < 0:
                 signal = 'SELL'
                 reason = '动量趋势: EMA20 死叉 EMA50 & MACD < 0'

        # ---------------------------------------------------------
        # 3. UKOUSD (原油) —— [支撑阻力突破策略]
        # 逻辑：当价格放量突破 R1 或跌破 S1 时触发信号。
        # ---------------------------------------------------------
        elif symbol == 'UKOUSD':
            # 做多信号: 突破 R1 (Breakout R1)
            if last_row['Close'] > last_row['R1'] and prev_row['Close'] <= prev_row['R1']:
                signal = 'BUY'
                reason = '突破策略: 价格突破 R1 阻力位'
            # 做空信号: 跌破 S1 (Breakdown S1)
            elif last_row['Close'] < last_row['S1'] and prev_row['Close'] >= prev_row['S1']:
                signal = 'SELL'
                reason = '突破策略: 价格跌破 S1 支撑位'
                
        # ---------------------------------------------------------
        # 4. CHINA50 (A50) —— [分时波动率策略]
        # 逻辑：价格站稳 VWAP 上方且 ATR 放大时做多。
        # ---------------------------------------------------------
        elif symbol == 'CHINA50':
            # ATR 放大: 当前 ATR > 过去5根 ATR 均值 (ATR Expanding)
            atr_rising = last_row['ATR'] > df['ATR'].rolling(5).mean().iloc[-1]
            
            # 做多信号 (Long Signal)
            if last_row['Close'] > last_row['VWAP'] and atr_rising:
                signal = 'BUY'
                reason = '波动率策略: 价格 > VWAP & ATR 放大'
            
            # (未定义做空逻辑，保持观望)

        # ---------------------------------------------------------
        # 信号过滤系统 (Signal Filtering)
        # ---------------------------------------------------------
        if signal in ['BUY', 'SELL']:
            atr = last_row['ATR']
            
            # 止损 (SL) 逻辑: 统一使用 2 * ATR(14) 作为动态保护位
            sl_dist = 2 * atr
            
            if signal == 'BUY':
                sl = entry_price - sl_dist
                # 止盈 (TP) 逻辑: 初始设为风险额度的 2.5 倍
                risk = entry_price - sl
                tp = entry_price + (2.5 * risk)
            else:
                sl = entry_price + sl_dist
                risk = sl - entry_price
                tp = entry_price - (2.5 * risk)
                
            # 盈亏比 (RR Ratio) 检查
            # R = |TP - Entry| / |Entry - SL|
            # 若 R < 2.0，该信号将被自动丢弃
            rr = abs(tp - entry_price) / abs(entry_price - sl)
            
            if rr < 2.0:
                return {'signal': 'WAIT', 'reason': f'盈亏比不足 (RR {rr:.2f} < 2.0)'}
                
            return {
                'signal': signal,
                'symbol': symbol,
                'price': entry_price,
                'sl': sl,
                'tp': tp,
                'rr': rr,
                'reason': reason,
                'time': last_row.name
            }
            
        return {'signal': 'WAIT', 'reason': '无信号 (No setup)'}
