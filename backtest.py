import pandas as pd
import numpy as np
from engine import StrategyEngine

class Backtester:
    def __init__(self):
        self.engine = StrategyEngine()

    def run_backtest(self, symbol, df, initial_capital=10000):
        """
        运行回测
        :param symbol: 交易品种
        :param df: 历史数据 (DataFrame with OHLCV)
        :param initial_capital: 初始资金
        :return: 回测结果字典
        """
        if df.empty:
            return None

        # 1. 计算所有指标
        df = self.engine.calculate_indicators(df)
        df = self.engine.calculate_pivots(df)
        
        trades = []
        active_trade = None
        equity = initial_capital
        
        # 遍历历史数据 (从第 50 行开始，确保有足够数据计算指标)
        for i in range(50, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            current_time = df.index[i]
            
            # 检查是否有持仓
            if active_trade:
                # 检查止盈止损
                result = self._check_exit(active_trade, current_bar)
                if result:
                    # 交易结束
                    pnl = result['pnl']
                    equity += pnl
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'symbol': symbol,
                        'type': active_trade['type'],
                        'entry_price': active_trade['entry_price'],
                        'exit_price': result['exit_price'],
                        'pnl': pnl,
                        'reason': result['reason'],
                        'equity': equity
                    })
                    active_trade = None
                continue # 持仓期间不新开仓 (简化逻辑：单品种单向持仓)
            
            # 生成信号
            # 我们需要构造一个临时的 df 切片来模拟"当时"的状态，
            # 或者重构 engine.check_signal 以接受单行数据。
            # 为了性能，我们在 engine 外部复用信号逻辑。
            # 这里我们直接复用 engine.check_signal 中的逻辑判断，但基于预计算的指标。
            
            signal_data = self._check_signal_at_index(symbol, df, i)
            
            if signal_data['signal'] in ['BUY', 'SELL']:
                entry_price = current_bar['Close'] # 简化：以收盘价入场
                # 如果是实盘，通常是下一根 Open 或即时。这里假设收盘确认信号后立即入场。
                
                # 重新计算 SL/TP (Engine 返回了，但我们可以直接用)
                sl = signal_data['sl']
                tp = signal_data['tp']
                
                # 资金管理：固定手数或风险比例？
                # 简化：每次交易 1 手 (Contract) 或 1 单位
                # PnL = (Exit - Entry) * Direction
                
                active_trade = {
                    'entry_time': current_time,
                    'type': signal_data['signal'],
                    'entry_price': entry_price,
                    'sl': sl,
                    'tp': tp,
                    'rr': signal_data['rr']
                }

        # 统计结果
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'trades': []
            }
            
        df_trades = pd.DataFrame(trades)
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]
        
        win_rate = len(wins) / len(trades) if len(trades) > 0 else 0
        total_pnl = df_trades['pnl'].sum()
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'trades': df_trades,
            'final_equity': equity
        }

    def _check_exit(self, trade, bar):
        """
        检查当前 K 线是否触发止盈止损
        """
        # 检查顺序：
        # 1. 如果 Low < SL (Long) 或 High > SL (Short) -> 止损
        # 2. 如果 High > TP (Long) 或 Low < TP (Short) -> 止盈
        # 假设：如果一根 K 线同时触发 SL 和 TP，通常假设先触发 SL (保守估计)
        
        if trade['type'] == 'BUY':
            # 止损检查
            if bar['Low'] <= trade['sl']:
                return {'exit_price': trade['sl'], 'pnl': trade['sl'] - trade['entry_price'], 'reason': 'Stop Loss'}
            # 止盈检查
            if bar['High'] >= trade['tp']:
                return {'exit_price': trade['tp'], 'pnl': trade['tp'] - trade['entry_price'], 'reason': 'Take Profit'}
                
        elif trade['type'] == 'SELL':
            # 止损检查
            if bar['High'] >= trade['sl']:
                return {'exit_price': trade['sl'], 'pnl': trade['entry_price'] - trade['sl'], 'reason': 'Stop Loss'}
            # 止盈检查
            if bar['Low'] <= trade['tp']:
                return {'exit_price': trade['tp'], 'pnl': trade['entry_price'] - trade['tp'], 'reason': 'Take Profit'}
                
        return None

    def _check_signal_at_index(self, symbol, df, i):
        """
        在特定索引处检查信号 (复用 engine 逻辑)
        """
        # 为了不完全重写逻辑，我们调用 engine.check_signal
        # 但传递截止到 i 的切片是低效的。
        # 更好的方式是将 engine 的逻辑解耦，或者在这里简单重写一遍判断。
        # 鉴于 engine.py 逻辑不多，我们在 backtester 中适配一下。
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # 构造一个假的小 df 用于 engine (如果 engine 需要 rolling 等，切片必须够长)
        # 但我们已经计算好了指标，直接判断即可。
        
        signal = 'WAIT'
        reason = ''
        
        # 1. XAUUSD & XAGUSD
        if symbol in ['XAUUSD', 'XAGUSD']:
            if row['Close'] < row['BB_Low'] and row['RSI'] < 30:
                signal = 'BUY'
            elif row['Close'] > row['BB_High'] and row['RSI'] > 70:
                signal = 'SELL'
                
        # 2. NAS100
        elif symbol == 'NAS100':
            cross_up = prev_row['EMA_20'] <= prev_row['EMA_50'] and row['EMA_20'] > row['EMA_20'] # Typo in engine logic reproduction? 
            # Original: last_row['EMA_20'] > last_row['EMA_50']
            cross_up = prev_row['EMA_20'] <= prev_row['EMA_50'] and row['EMA_20'] > row['EMA_50']
            
            if cross_up and row['MACD_Hist'] > 0:
                signal = 'BUY'
            # Short logic (optional in engine)
            elif prev_row['EMA_20'] >= prev_row['EMA_50'] and row['EMA_20'] < row['EMA_50'] and row['MACD_Hist'] < 0:
                 signal = 'SELL'

        # 3. UKOUSD
        elif symbol == 'UKOUSD':
            if row['Close'] > row['R1'] and prev_row['Close'] <= prev_row['R1']:
                signal = 'BUY'
            elif row['Close'] < row['S1'] and prev_row['Close'] >= prev_row['S1']:
                signal = 'SELL'

        # 4. CHINA50
        elif symbol == 'CHINA50':
            # ATR Rising check needs rolling mean
            # df['ATR'] is already calculated.
            # rolling mean needs previous 5.
            # Let's calculate simple mean of last 5 manually
            atr_hist = df['ATR'].iloc[i-5:i]
            if len(atr_hist) == 5:
                atr_mean = atr_hist.mean()
                atr_rising = row['ATR'] > atr_mean
                
                if row['Close'] > row['VWAP'] and atr_rising:
                    signal = 'BUY'

        # SL/TP Calc
        sl = 0.0
        tp = 0.0
        rr = 0.0
        
        if signal in ['BUY', 'SELL']:
            atr = row['ATR']
            sl_dist = 2 * atr
            entry_price = row['Close']
            
            if signal == 'BUY':
                sl = entry_price - sl_dist
                risk = entry_price - sl
                tp = entry_price + (2.5 * risk)
            else:
                sl = entry_price + sl_dist
                risk = sl - entry_price
                tp = entry_price - (2.5 * risk)
                
            rr = abs(tp - entry_price) / abs(entry_price - sl) if abs(entry_price - sl) > 0 else 0
            
            if rr < 2.0:
                signal = 'WAIT'
                
        return {'signal': signal, 'sl': sl, 'tp': tp, 'rr': rr}
