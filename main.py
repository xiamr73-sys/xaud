import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import threading
from datetime import datetime
from data import DataProvider
from engine import StrategyEngine
from notifier import send_discord_alert, send_trade_close_alert
from backtest import Backtester

# Page Config
st.set_page_config(page_title="量化策略监控", layout="wide")

# Singleton for Data and Engine
class MarketMonitor:
    def __init__(self):
        self.data_provider = DataProvider()
        self.engine = StrategyEngine()
        self.symbols = ['XAUUSD', 'XAGUSD', 'NAS100', 'UKOUSD', 'CHINA50']
        self.data_store = {s: pd.DataFrame() for s in self.symbols}
        self.signals = {s: {'signal': 'WAIT'} for s in self.symbols}
        self.last_sent_signals = {s: None for s in self.symbols} # Track last sent signal state
        
        # Active trades tracking for Live TP/SL monitoring
        # Format: {symbol: {'type': 'BUY', 'entry': 100, 'sl': 90, 'tp': 120}}
        self.active_trades = {} 
        
        self.last_update = None
        self.running = False
        self.lock = threading.Lock()

    def start_polling(self, interval=60):
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self._poll_loop, args=(interval,), daemon=True)
        thread.start()

    def _poll_loop(self, interval):
        while self.running:
            for symbol in self.symbols:
                # Fetch data (enough for indicators)
                df = self.data_provider.get_latest_data(symbol, timeframe='1d', n=200)
                
                with self.lock:
                    self.data_store[symbol] = df
                    # Generate Signal
                    sig = self.engine.check_signal(symbol, df)
                    self.signals[symbol] = sig
                    
                    # Check for Notification (New Entry)
                    self._check_and_notify(symbol, sig)
                    
                    # Check Active Trades (TP/SL)
                    self._check_trade_management(symbol, df)
            
            self.last_update = datetime.now()
            time.sleep(interval)
            
    def _check_and_notify(self, symbol, current_signal):
        """
        Check if a new signal should trigger a Discord notification.
        """
        sig_type = current_signal.get('signal')
        
        # Only notify on valid BUY/SELL signals
        if sig_type in ['BUY', 'SELL']:
            last_sent = self.last_sent_signals.get(symbol)
            
            should_send = False
            if last_sent is None:
                should_send = True
            elif last_sent != sig_type:
                should_send = True
                
            if should_send:
                # Send Notification
                send_discord_alert(current_signal)
                # Update state
                self.last_sent_signals[symbol] = sig_type
                
                # Register as Active Trade for monitoring
                self.active_trades[symbol] = {
                    'type': sig_type,
                    'entry': current_signal.get('price'),
                    'sl': current_signal.get('sl'),
                    'tp': current_signal.get('tp')
                }
        else:
            if sig_type == 'WAIT':
                self.last_sent_signals[symbol] = 'WAIT'
                
    def _check_trade_management(self, symbol, df):
        """
        Check if current price hits TP or SL of active trades.
        """
        if symbol not in self.active_trades:
            return
            
        trade = self.active_trades[symbol]
        if df.empty:
            return
            
        current_price = df['Close'].iloc[-1]
        # Ideally check High/Low of current bar if we want intraday precision,
        # but for snapshot monitoring, Close is safer to avoid noise or using last tick.
        # Let's use Close for now.
        
        result = None
        pnl = 0
        
        if trade['type'] == 'BUY':
            if current_price <= trade['sl']:
                result = 'Stop Loss'
                pnl = trade['sl'] - trade['entry']
            elif current_price >= trade['tp']:
                result = 'Take Profit'
                pnl = trade['tp'] - trade['entry']
        elif trade['type'] == 'SELL':
            if current_price >= trade['sl']:
                result = 'Stop Loss'
                pnl = trade['entry'] - trade['sl']
            elif current_price <= trade['tp']:
                result = 'Take Profit'
                pnl = trade['entry'] - trade['tp']
                
        if result:
            # Trigger Alert
            trade_data = {
                'symbol': symbol,
                'result': result,
                'pnl': pnl,
                'exit_price': current_price # or trade['tp'] / trade['sl']
            }
            send_trade_close_alert(trade_data)
            
            # Remove from active trades
            del self.active_trades[symbol]
            # Reset last sent signal so we can re-enter if signal persists?
            # Or keep it as is. Usually strategy might still signal BUY. 
            # If we delete it here, _check_and_notify might see "BUY" again and re-enter immediately if signal condition still holds.
            # To avoid re-entry on same bar, we should rely on last_sent_signals state.
            # But if we closed it, maybe we want to wait for 'WAIT' before 'BUY' again.
            self.last_sent_signals[symbol] = 'WAIT' # Force reset to wait for new setup

    def get_data(self, symbol):
        with self.lock:
            return self.data_store.get(symbol, pd.DataFrame()).copy()

    def get_signal(self, symbol):
        with self.lock:
            return self.signals.get(symbol, {}).copy()
            
    def get_all_signals(self):
        with self.lock:
            return self.signals.copy()

# Initialize Monitor
@st.cache_resource
def get_monitor():
    monitor = MarketMonitor()
    monitor.start_polling(interval=10) # 10s polling for demo
    return monitor

monitor = get_monitor()

# UI Layout
st.title("实时量化策略监控系统")

# Sidebar - Navigation
page = st.sidebar.radio("功能导航", ["实时监控", "历史回测"])

status_container = st.sidebar.container()

if page == "实时监控":
    # Main Area
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("行情深度分析")
        selected_symbol = st.selectbox("选择交易品种", monitor.symbols)
        
        # Plotly Chart
        df = monitor.get_data(selected_symbol)
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'])])
            
            df_ind = monitor.engine.calculate_indicators(df)
            
            if selected_symbol in ['XAUUSD', 'XAGUSD']:
                fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['BB_High'], line=dict(color='gray', width=1), name='BB上轨'))
                fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['BB_Low'], line=dict(color='gray', width=1), name='BB下轨'))
                
            elif selected_symbol == 'NAS100':
                fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['EMA_20'], line=dict(color='orange', width=1), name='EMA 20均线'))
                fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['EMA_50'], line=dict(color='blue', width=1), name='EMA 50均线'))
                
            elif selected_symbol == 'CHINA50':
                fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['VWAP'], line=dict(color='purple', width=1), name='VWAP均价'))
                
            fig.update_layout(title=f"{selected_symbol} K线走势图", xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display Signal Details
            sig = monitor.get_signal(selected_symbol)
            st.info(f"当前信号状态: {sig.get('signal', 'WAIT')} - {sig.get('reason', '')}")
            if sig.get('signal') in ['BUY', 'SELL']:
                 st.write(f"建议入场: {sig.get('price')}, 止损(SL): {sig.get('sl')}, 止盈(TP): {sig.get('tp')}, 盈亏比(RR): {sig.get('rr'):.2f}")

        else:
            st.warning("正在获取数据，请稍候...")

    with col2:
        st.subheader("高盈亏比机会榜")
        all_signals = monitor.get_all_signals()
        valid_signals = []
        for sym, s in all_signals.items():
            if s.get('signal') in ['BUY', 'SELL']:
                valid_signals.append(s)
                
        if valid_signals:
            for s in valid_signals:
                st.success(f"{s['symbol']} {s['signal']}")
                st.caption(f"盈亏比: {s.get('rr'):.2f} | 理由: {s['reason']}")
                st.markdown("---")
        else:
            st.write("暂无活跃信号")
            
elif page == "历史回测":
    st.header("策略历史回测")
    st.write("使用历史数据验证策略表现，并检查止盈止损触发情况。")
    
    col_bt_1, col_bt_2 = st.columns(2)
    with col_bt_1:
        bt_symbol = st.selectbox("回测品种", monitor.symbols, key='bt_symbol')
    with col_bt_2:
        bt_days = st.number_input("回测天数", min_value=30, max_value=365, value=100)
        
    if st.button("开始回测"):
        with st.spinner(f"正在回测 {bt_symbol} ..."):
            # Fetch data for backtest
            # Using data provider but requesting more data
            # Note: yfinance limits, daily is fine for 1y.
            
            # We need to create a new instance or reuse provider logic
            # Since get_latest_data returns limited n, let's call it with larger n
            # Assuming daily candles
            n_candles = bt_days + 50 # buffer for indicators
            
            df_bt = monitor.data_provider.get_latest_data(bt_symbol, timeframe='1d', n=n_candles)
            
            if df_bt.empty:
                st.error("无法获取足够的历史数据进行回测。")
            else:
                backtester = Backtester()
                result = backtester.run_backtest(bt_symbol, df_bt)
                
                if result and result['total_trades'] > 0:
                    # Metrics
                    m1, m2, m3 = st.columns(3)
                    m1.metric("总交易次数", result['total_trades'])
                    m1.metric("胜率", f"{result['win_rate']:.1%}")
                    m2.metric("总盈亏 (点数/金额)", f"{result['total_pnl']:.2f}")
                    m3.metric("最终权益 (初始1W)", f"{result['final_equity']:.2f}")
                    
                    # Trade Log
                    st.subheader("交易记录")
                    st.dataframe(result['trades'])
                    
                    # Equity Curve
                    # Reconstruct equity curve from trades
                    # Simple plot
                    trades_df = result['trades']
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(x=trades_df['exit_time'], y=trades_df['equity'], mode='lines+markers', name='权益曲线'))
                    fig_eq.update_layout(title="资金曲线", xaxis_title="时间", yaxis_title="权益")
                    st.plotly_chart(fig_eq, use_container_width=True)
                    
                else:
                    st.warning("在选定周期内未产生符合条件的交易信号。")


# Update Sidebar Status (Common for all pages)
with status_container:
    st.sidebar.header("市场状态监控")
    for sym in monitor.symbols:
        s = monitor.get_signal(sym)
        status = s.get('signal', 'WAIT')
        color = "🟢" if status == 'BUY' else "🔴" if status == 'SELL' else "⚪"
        st.write(f"{color} {sym}: {status}")

# Auto-refresh logic (Only for Monitor page usually, but kept global for simplicity)
if page == "实时监控":
    time.sleep(1)
    st.rerun()
