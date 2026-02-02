import pandas as pd

def calculate_kdj(df, period=9, k_period=3, d_period=3):
    """
    计算 KDJ 指标
    """
    df = df.copy()
    
    # 计算 RSV
    df['low_min'] = df['low'].rolling(window=period).min()
    df['high_max'] = df['high'].rolling(window=period).max()
    df['rsv'] = (df['close'] - df['low_min']) / (df['high_max'] - df['low_min']) * 100
    df['rsv'] = df['rsv'].fillna(0) # 处理 NaN
    
    k_values = []
    d_values = []
    
    k = 50
    d = 50
    
    for rsv in df['rsv']:
        k = (2/3) * k + (1/3) * rsv
        d = (2/3) * d + (1/3) * k
        k_values.append(k)
        d_values.append(d)
        
    df['k'] = k_values
    df['d'] = d_values
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    return df

def check_comprehensive_strategy(df):
    """
    原始综合策略：
    1. 均线多头 (MA5>MA10>MA20)
    2. 放量 (Vol > 2 * MA5_Vol)
    3. 回踩支撑 (Close 接近 MA20)
    4. KDJ 金叉
    """
    if len(df) < 22: return False
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 1. 均线多头
    if not (latest['ma5'] > latest['ma10'] and latest['ma10'] > latest['ma20']):
        return False
        
    # 2. 放量
    vol_ma5_past = df['volume'].iloc[-6:-1].mean()
    if vol_ma5_past == 0 or latest['volume'] <= 2 * vol_ma5_past:
        return False
        
    # 3. 回踩 MA20
    if latest['ma20'] == 0: return False
    diff_pct = abs(latest['close'] - latest['ma20']) / latest['ma20']
    if diff_pct > 0.03:
        return False
        
    # 4. KDJ 金叉
    if not (prev['k'] < prev['d'] and latest['k'] > latest['d']):
        return False
        
    return True

def check_old_duck_head(df):
    """
    老鸭头模型：
    1. 均线金叉后回踩：MA5/MA10 穿过 MA60
    2. 股价回踩 60 日线不破
    """
    if len(df) < 60: return False
    
    latest = df.iloc[-1]
    
    # 必须有 MA60
    if pd.isna(latest['ma60']) or latest['ma60'] == 0:
        return False
        
    # 当前 MA5, MA10 > MA60 (多头排列)
    if not (latest['ma5'] > latest['ma60'] and latest['ma10'] > latest['ma60']):
        return False
        
    # 股价回踩 60 日线：最低价触及 60 日线附近（例如 1.02 倍以内），且收盘价 > 60 日线（未有效跌破）
    is_touching = latest['low'] <= latest['ma60'] * 1.02
    is_holding = latest['close'] >= latest['ma60']
    
    return is_touching and is_holding

def check_platform_breakout(df):
    """
    底部放量V型反转/平台突破：
    1. 股价在低位横盘 20 天以上
    2. 突然单日涨幅 > 5% 
    3. 成交量翻倍
    """
    if len(df) < 22: return False
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 单日涨幅 > 5%
    if latest['pct_chg'] <= 5:
        return False
        
    # 成交量翻倍 (对比昨日)
    if prev['volume'] == 0 or latest['volume'] <= 2 * prev['volume']:
        return False
        
    # 底部横盘 20 天以上
    past_20 = df.iloc[-21:-1]
    high_max = past_20['high'].max()
    low_min = past_20['low'].min()
    
    if low_min == 0: return False
    
    amplitude = (high_max - low_min) / low_min
    is_sideways = amplitude < 0.20
    
    return is_sideways

def check_dragon_turns_head(df):
    """
    龙回头：
    1. 过去 10 天内有过 2 个涨停板
    2. 当前连续 3 天缩量下跌
    3. 触及 10 日线
    """
    if len(df) < 15: return False
    
    latest = df.iloc[-1]
    
    # 1. 过去 10 天内
    recent_10 = df.iloc[-10:]
    limit_up_count = len(recent_10[recent_10['pct_chg'] > 9.5])
    if limit_up_count < 2:
        return False
        
    # 2. 当前连续 3 天缩量下跌
    day0 = df.iloc[-1]
    day1 = df.iloc[-2]
    day2 = df.iloc[-3]
    
    is_falling = (day0['pct_chg'] < 0) and (day1['pct_chg'] < 0) and (day2['pct_chg'] < 0)
    is_shrinking = (day0['volume'] < day1['volume']) and (day1['volume'] < day2['volume'])
    
    if not (is_falling and is_shrinking):
        return False
        
    # 3. 触及 10 日线
    if day0['ma10'] == 0: return False
    is_touching_ma10 = (day0['low'] <= day0['ma10'] * 1.02) and (day0['close'] >= day0['ma10'] * 0.98)
    
    return is_touching_ma10
