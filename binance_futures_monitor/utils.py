# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import ta
from loguru import logger

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算技术指标并添加到 DataFrame 中。
    
    包含指标:
    1. Bollinger Bands (布林带, 20, 2.0)
    2. ATR (平均真实波幅, 14)
    3. Keltner Channels (肯特纳通道, 20, 1.5)
    4. MACD (12, 26, 9)
    5. RSI (14)
    6. EMA (20)
    """
    try:
        if df.empty or len(df) < 26:
            logger.warning("数据不足，无法计算完整指标")
            return df

        # 1. 计算布林带 (Bollinger Bands)
        indicator_bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2.0)
        df['BBU'] = indicator_bb.bollinger_hband()
        df['BBL'] = indicator_bb.bollinger_lband()
        df['BBM'] = indicator_bb.bollinger_mavg()
        df['BBW'] = indicator_bb.bollinger_wband()

        # 2. 计算 ATR (Average True Range)
        indicator_atr = ta.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
        df['ATR'] = indicator_atr.average_true_range()

        # 3. 计算肯特纳通道 (Keltner Channels)
        kc_mid = ta.trend.ema_indicator(close=df["close"], window=20)
        kc_atr = ta.volatility.average_true_range(high=df["high"], low=df["low"], close=df["close"], window=20)
        multiplier = 1.5
        df['KCU'] = kc_mid + (multiplier * kc_atr)
        df['KCL'] = kc_mid - (multiplier * kc_atr)
        df['KCM'] = kc_mid

        # 4. 计算成交量均线
        indicator_vol_sma = ta.trend.SMAIndicator(close=df["volume"], window=20)
        df['VOL_SMA_20'] = indicator_vol_sma.sma_indicator()

        # 5. 计算 OBV
        indicator_obv = ta.volume.OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"])
        df['OBV'] = indicator_obv.on_balance_volume()
        df['OBV_SMA_20'] = df['OBV'].rolling(window=20).mean()

        # 6. 计算 RSI
        indicator_rsi = ta.momentum.RSIIndicator(close=df["close"], window=14)
        df['RSI'] = indicator_rsi.rsi()

        # 7. 计算 EMA
        df['EMA_20'] = ta.trend.ema_indicator(close=df["close"], window=20)
        
        # 8. 计算 MACD
        indicator_macd = ta.trend.MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = indicator_macd.macd()
        df['MACD_SIGNAL'] = indicator_macd.macd_signal()
        df['MACD_HIST'] = indicator_macd.macd_diff()
        
        # 9. 计算价格斜率 (Linear Regression Slope of Close over last 5 periods)
        # normalize slope by price to make it comparable: (Slope / Price) * 100
        # ta library has linear regression indicator? No direct "slope" in simple ta.
        # Use numpy polyfit for last 5 points
        # To make it efficient, we only calculate for the last few rows or use rolling apply (slow)
        # Simple approximation: ROC (Rate of Change) of 3 periods smoothed
        # Or simple: (Close - Close_N) / N
        # Let's use simple ROC for efficiency as "Slope Proxy"
        # 5-period ROC: ((Close - Close_5) / Close_5) * 100
        df['PRICE_SLOPE_PCT'] = df['close'].pct_change(periods=5) * 100

        return df

    except Exception as e:
        logger.error(f"计算指标时发生错误: {e}")
        return df

def check_volume_surge(df) -> bool:
    """
    检查成交量激增
    当前 15m 成交量 > 过去 1 小时 (4根K线) 平均成交量的 3 倍
    """
    try:
        if len(df) < 6:
            return False
            
        current_vol = df['volume'].iloc[-1]
        # 过去 1 小时 = 过去 4 根 (不含当前)
        # iloc[-5:-1] 取倒数第5根到倒数第2根 (共4根)
        past_1h_vol_avg = df['volume'].iloc[-5:-1].mean()
        
        if past_1h_vol_avg == 0:
            return False
            
        return current_vol > (3.0 * past_1h_vol_avg)
    except Exception:
        return False

def check_momentum_buildup(row, df) -> bool:
    """
    RSI 与价格斜率共振
    条件:
    1. 50 < RSI < 70 (上升初期，未超买)
    2. 价格斜率陡峭上升 (这里用 5周期涨幅 > 1% 作为"陡峭"的简单定义，对于15m级别已经很快了)
    """
    try:
        rsi = row.get('RSI', 50)
        slope_pct = row.get('PRICE_SLOPE_PCT', 0)
        
        rsi_condition = 50 < rsi < 70
        # 5根K线涨幅超过 1.5% 算陡峭
        slope_condition = slope_pct > 1.5 
        
        return rsi_condition and slope_condition
    except Exception:
        return False

def check_macd_golden_cross(df) -> bool:
    """
    检查 MACD 是否刚发生金叉 (当前 MACD > Signal 且 上一根 MACD <= Signal)
    """
    try:
        if len(df) < 2:
            return False
            
        curr_macd = df['MACD'].iloc[-1]
        curr_sig = df['MACD_SIGNAL'].iloc[-1]
        prev_macd = df['MACD'].iloc[-2]
        prev_sig = df['MACD_SIGNAL'].iloc[-2]
        
        # 金叉: 此时 MACD 上穿 Signal
        golden_cross = (curr_macd > curr_sig) and (prev_macd <= prev_sig)
        
        return golden_cross
    except Exception:
        return False

def check_1m_trigger(df_1m: pd.DataFrame, oi_change_1m: float) -> tuple[bool, str]:
    """
    检查 1分钟 级别的异动信号 (高频扫描)
    
    条件:
    1. 价格异动: 1分钟涨幅在 0.3% - 1.2% 之间 (刚启动，未飞远)
    2. 成交量异动: 当前量 > 3 * 过去10分钟均量
    3. 持仓量异动: 1分钟 OI 净增 > 0.05% (可选，或作为加分项)
    
    Returns:
        (is_triggered, reason_msg)
    """
    try:
        if df_1m.empty or len(df_1m) < 15:
            return False, ""
            
        latest = df_1m.iloc[-1]
        close = latest['close']
        open_p = latest['open']
        volume = latest['volume']
        
        # 1. 价格涨幅 (0.3% ~ 1.2%)
        change_pct = (close - open_p) / open_p * 100
        is_price_active = 0.3 <= change_pct <= 1.2
        
        # 2. 成交量激增
        # 计算过去 10 根 K 线的平均成交量 (不含当前)
        past_vol_avg = df_1m['volume'].iloc[-11:-1].mean()
        is_vol_active = False
        if past_vol_avg > 0:
            is_vol_active = volume > (3.0 * past_vol_avg)
            
        # 3. OI 异动 (作为辅助确认，或者独立触发)
        # 1分钟级别 OI 变化通常很小，> 0.05% 算显著
        is_oi_active = oi_change_1m > 0.05
        
        # 触发逻辑:
        # A. 量价齐升 (价格启动 + 放量)
        if is_price_active and is_vol_active:
            return True, f"1m量价齐升(涨{change_pct:.2f}%, 量{volume/past_vol_avg:.1f}x)"
            
        # B. 巨量抢筹 (价格微涨 + 巨量 + OI增加)
        if (change_pct > 0.1) and (volume > 5.0 * past_vol_avg) and is_oi_active:
            return True, f"1m巨量抢筹(量{volume/past_vol_avg:.1f}x, OI+{oi_change_1m:.2f}%)"
            
        # C. 纯 OI 暴增 (价格未动，主力潜伏)
        if is_oi_active and (oi_change_1m > 0.2): # 0.2% in 1m is huge
            return True, f"1m持仓暴增(OI+{oi_change_1m:.2f}%)"
            
        return False, ""
        
    except Exception as e:
        logger.error(f"1m check error: {e}")
        return False, ""



def check_squeeze(row) -> bool:
    """
    检查是否处于 Squeeze 状态 (布林带完全位于肯特纳通道内部)
    
    Condition:
        BBU < KCU  AND  BBL > KCL
    """
    try:
        return (row['BBU'] < row['KCU']) and (row['BBL'] > row['KCL'])
    except Exception:
        return False

def check_main_force_lurking(price_volatility: float, oi_change_pct: float, obv_trend: bool) -> bool:
    """
    判断是否主力潜伏
    
    Condition:
        1. 价格波幅 < 1% (横盘)
        2. 持仓量增长 > 1.0% (资金流入)
        3. OBV 趋势向上 (吸筹确认，过滤假突破)
    """
    return (abs(price_volatility) < 1.0) and (oi_change_pct > 1.0) and obv_trend

def check_trend_breakout(row, df) -> bool:
    """
    检查是否处于强劲趋势突破形态 (Catch the Pump)
    
    特征:
    1. 价格强势: 收盘价 > EMA20 (多头排列)
    2. 动能爆发: RSI > 60 (进入强势区，但未必超买)
    3. 突破布林带: 收盘价接近或突破布林上轨 (BBU)
    4. 成交量放大: 当前 Volume > 1.5 * VOL_SMA_20
    """
    try:
        close = row['close']
        ema20 = row.get('EMA_20', 0)
        bbu = row['BBU']
        rsi = row.get('RSI', 50)
        volume = row['volume']
        vol_sma = row.get('VOL_SMA_20', 0)
        
        # 1. 趋势向上
        trend_up = close > ema20
        
        # 2. 动能强劲 (RSI > 60 表示进入拉升段)
        momentum_strong = rsi > 60
        
        # 3. 价格在布林带上轨附近 (突破或贴行)
        # 允许稍微低一点点 (0.995)，捕捉刚启动的瞬间
        near_upper_band = close >= (bbu * 0.995)
        
        # 4. 放量 (是均量的 1.5 倍以上)
        volume_surge = volume > (vol_sma * 1.5)
        
        return trend_up and momentum_strong and near_upper_band and volume_surge
    except Exception:
        return False

def check_obv_trend(df) -> bool:
    """
    检查 OBV 是否呈现 45 度角向上 (强势吸筹)
    
    逻辑 (放宽版):
    1. OBV 当前值 > OBV_SMA_20 (处于上升趋势)
    2. 整体趋势向上: 当前 OBV 高于 3 周期前 (允许中间有微小回调，不再要求连续3根严苛上涨)
    """
    try:
        if len(df) < 5:
            return False
            
        obv = df['OBV']
        obv_sma = df['OBV_SMA_20']
        
        # 1. 趋势向上 (位于均线上方)
        if obv.iloc[-1] <= obv_sma.iloc[-1]:
            return False
            
        # 2. 近期趋势向上 (放宽：不再要求每根都涨，只要当前比3根前高即可)
        # 这样允许中间有一根小的阴线回调
        is_rising = obv.iloc[-1] > obv.iloc[-3]
        
        return is_rising
    except Exception:
        return False

def calculate_score(squeeze_active: bool, lurking_active: bool, volume_flow_active: bool, breakout_active: bool = False, vol_surge_active: bool = False, momentum_active: bool = False, new_top_bull_active: bool = False) -> int:
    """
    计算综合评分 (v2.0 升级版)
    
    Score 规则:
    - Squeeze (挤压/蓄势): 40分
    - Lurking (潜伏/吸筹): 40分
    - Volume Flow (量能): 20分
    - Breakout (突破/主升浪): 50分
    - Vol Surge (成交量激增): +30分 (新增)
    - Momentum (动能/斜率): +30分 (新增)
    - New Top Bull (新晋榜单+金叉): +50分 (新增, 强力信号)
    """
    score = 0
    
    if new_top_bull_active:
        score += 50
    
    if breakout_active:
        score += 50
        
    if vol_surge_active:
        score += 30
        
    if momentum_active:
        score += 30
        
    if squeeze_active:
        score += 40
        
    if lurking_active:
        score += 40
        
    if volume_flow_active:
        score += 20
        
    return score

def calculate_trade_params(row):
    """
    计算交易建议参数 (止损, 止盈, 盈亏比)
    
    Args:
        row: 包含 BBU, BBL, ATR, close 的 Series
        
    Returns:
        dict: 包含多/空方向的建议参数
    """
    try:
        close = row['close']
        atr = row['ATR']
        bbu = row['BBU']
        bbl = row['BBL']
        
        if pd.isna(atr) or atr == 0:
            return None

        # --- 多单建议 (Long) ---
        # 止损: 布林带下轨下方 0.3 * ATR
        long_sl = bbl - (0.3 * atr)
        # 止盈1: +1.5 * ATR (相对于入场价，这里假设入场价为当前收盘价)
        long_tp1 = close + (1.5 * atr)
        # 止盈2: +3.0 * ATR
        long_tp2 = close + (3.0 * atr)
        
        # 盈亏比 (Risk/Reward Ratio)
        # Risk = Close - SL
        # Reward (conservative) = TP1 - Close
        long_risk = close - long_sl
        long_reward = long_tp1 - close
        long_rr = long_reward / long_risk if long_risk > 0 else 0

        # --- 空单建议 (Short) ---
        # 止损: 布林带上轨上方 0.3 * ATR
        short_sl = bbu + (0.3 * atr)
        # 止盈1: -1.5 * ATR
        short_tp1 = close - (1.5 * atr)
        # 止盈2: -3.0 * ATR
        short_tp2 = close - (3.0 * atr)
        
        # 盈亏比
        # Risk = SL - Close
        # Reward = Close - TP1
        short_risk = short_sl - close
        short_reward = close - short_tp1
        short_rr = short_reward / short_risk if short_risk > 0 else 0

        return {
            "long": {
                "sl": long_sl,
                "tp1": long_tp1,
                "tp2": long_tp2,
                "rr": long_rr
            },
            "short": {
                "sl": short_sl,
                "tp1": short_tp1,
                "tp2": short_tp2,
                "rr": short_rr
            }
        }

    except Exception as e:
        logger.warning(f"计算交易参数失败: {e}")
        return None
