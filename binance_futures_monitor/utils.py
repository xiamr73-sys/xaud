# -*- coding: utf-8 -*-
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
    
    Args:
        df (pd.DataFrame): 包含 'open', 'high', 'low', 'close', 'volume' 的 K 线数据
        
    Returns:
        pd.DataFrame: 包含计算出的指标的新 DataFrame
    """
    try:
        if df.empty or len(df) < 20:
            logger.warning("数据不足，无法计算完整指标")
            return df

        # 1. 计算布林带 (Bollinger Bands)
        # length=20, std=2.0
        indicator_bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2.0)
        df['BBU'] = indicator_bb.bollinger_hband()
        df['BBL'] = indicator_bb.bollinger_lband()
        df['BBM'] = indicator_bb.bollinger_mavg()
        # Band Width for reference
        df['BBW'] = indicator_bb.bollinger_wband()

        # 2. 计算 ATR (Average True Range)
        # length=14
        indicator_atr = ta.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
        df['ATR'] = indicator_atr.average_true_range()

        # 3. 计算肯特纳通道 (Keltner Channels)
        # 这里的 scalar 需要调整为 1.5 (原为 2.0)
        # original_multiplier=1.5 (对应 scalar)
        # ta 库的 KeltnerChannel 默认 multiplier 是 2.0，我们需要手动指定
        # 注意: ta 库较新版本的参数可能是 original_multiplier 或 multiplier，查看源码通常是 original_multiplier
        # 为了兼容性，我们直接用 ATR 手动算，或者尝试传参
        # 手动计算更稳健: KC_Mid = EMA(20), KC_Up = KC_Mid + 1.5*ATR(10), KC_Low = KC_Mid - 1.5*ATR(10)
        # 这里使用 ta 库的 ATR(10) 来配合 KC
        
        # 3.1 计算 KC 专用的 ATR (window=10 for standard KC, but user didn't specify ATR period for KC, defaulting to 10 is common)
        # 用户仅指定 KC(20, 1.5). 通常 KC 的 ATR 周期也是 20 或 10. 这里用 20 保持一致性? 
        # 常用设置: EMA 20, ATR 10, Multiplier 2.0.
        # 用户要求: 20, 1.5. 我们假设 ATR 周期也为 20 (或者 10). 
        # 让我们使用 ta 库，并传入 window=20.
        
        # ta library signature: KeltnerChannel(high, low, close, window=20, window_atr=10, original_multiplier=2, ...)
        # 我们需要 multiplier = 1.5
        # 注意：ta 库版本差异可能导致参数名不同，最稳妥的方式是手动计算，不依赖库的特定参数名
        
        # 手动计算 Keltner Channels (20, 1.5)
        # 1. 计算中轨: EMA(20)
        kc_mid = ta.trend.ema_indicator(close=df["close"], window=20)
        
        # 2. 计算 ATR(20) (通常 KC 使用 ATR 周期与 EMA 周期一致，或者使用 10)
        # 用户要求: 肯特纳通道 (20, 1.5). 这里假设 ATR 周期为 20.
        kc_atr = ta.volatility.average_true_range(high=df["high"], low=df["low"], close=df["close"], window=20)
        
        # 3. 计算上轨和下轨
        multiplier = 1.5
        df['KCU'] = kc_mid + (multiplier * kc_atr)
        df['KCL'] = kc_mid - (multiplier * kc_atr)
        df['KCM'] = kc_mid # 中轨

        # 4. 计算成交量均线 (用于 Volume Flow 评分)
        # SMA 20
        indicator_vol_sma = ta.trend.SMAIndicator(close=df["volume"], window=20)
        df['VOL_SMA_20'] = indicator_vol_sma.sma_indicator()

        # 5. 计算 OBV (On-Balance Volume)
        indicator_obv = ta.volume.OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"])
        df['OBV'] = indicator_obv.on_balance_volume()
        
        # 计算 OBV 的斜率 (使用最近 5 根 K 线的线性回归斜率，或者简单的变化率)
        # 这里用简单的 5 周期变化率近似斜率趋势
        # OBV_Slope = (OBV_now - OBV_5_ago) / OBV_5_ago * 100 (不严谨，因为 OBV 可以是负数)
        # 更好的方式：计算 OBV 的 SMA(5) 并比较当前值与 SMA 的关系，或者直接看涨势
        # 我们用 ta 库的趋势判断辅助，或者简单判断: OBV > OBV_SMA_20 且 OBV 在上涨
        # 为了符合 "45度角向上" 的描述，我们需要 OBV 呈现显著的上升趋势
        # 简单算法：最近 3 根 OBV 持续上涨，且累计涨幅显著
        
        # 使用 20 周期 OBV 均线作为基准
        df['OBV_SMA_20'] = df['OBV'].rolling(window=20).mean()

        return df

    except Exception as e:
        logger.error(f"计算指标时发生错误: {e}")
        return df

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

def calculate_score(squeeze_active: bool, lurking_active: bool, volume_flow_active: bool) -> int:
    """
    计算综合评分
    
    Score = (Squeeze_State * 40) + (OI_Growth * 40) + (Volume_Flow * 20)
    """
    score = 0
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
