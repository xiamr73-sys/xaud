import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta

# 尝试导入 MetaTrader5，如果不可用则处理失败（例如在 Mac 上）
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# 配置日志 (Configure logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataProvider:
    """
    数据提供者 (Data Provider)
    负责从 MetaTrader5 或 yfinance 获取行情数据。
    """
    def __init__(self, source='mt5'):
        self.source = source
        self.mt5_initialized = False
        
        # 符号映射表：将内部统一符号映射到特定数据源的符号
        # Mapping from internal symbol name to specific source symbol
        self.symbols_map = {
            'XAUUSD': {'mt5': 'XAUUSD', 'yf': 'GC=F'},     # 黄金 (Gold Futures)
            'XAGUSD': {'mt5': 'XAGUSD', 'yf': 'SI=F'},     # 白银 (Silver Futures)
            'NAS100': {'mt5': 'NAS100', 'yf': '^NDX'},     # 纳指100 (Nasdaq 100 Index)
            'UKOUSD': {'mt5': 'UKOUSD', 'yf': 'BZ=F'},     # 布伦特原油 (Brent Oil)
            'CHINA50': {'mt5': 'CHINA50', 'yf': 'FXI'}     # 中国A50 (Proxy: iShares China Large-Cap ETF)
        }

        # 初始化数据源 (Initialize Data Source)
        if self.source == 'mt5' and MT5_AVAILABLE:
            if not mt5.initialize():
                logging.error("MetaTrader5 初始化失败。回退到 yfinance。")
                self.source = 'yfinance'
            else:
                self.mt5_initialized = True
                logging.info("MetaTrader5 初始化成功。")
        elif self.source == 'mt5' and not MT5_AVAILABLE:
             logging.warning("未找到 MetaTrader5 包。回退到 yfinance。")
             self.source = 'yfinance'

    def get_latest_data(self, symbol, timeframe='1d', n=100):
        """
        获取最新的 n 根 K 线数据。
        Fetch latest n bars of data.
        timeframe: '1d', '1h', '15m', etc.
        """
        if self.source == 'mt5' and self.mt5_initialized:
            return self._get_mt5_data(symbol, timeframe, n)
        else:
            return self._get_yf_data(symbol, timeframe, n)

    def _get_mt5_data(self, symbol, timeframe, n):
        """从 MetaTrader5 获取数据"""
        mt5_symbol = self.symbols_map.get(symbol, {}).get('mt5', symbol)
        
        # 将时间周期字符串映射到 MT5 常量
        tf_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1,
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_D1)
        
        rates = mt5.copy_rates_from_pos(mt5_symbol, mt5_tf, 0, n)
        if rates is None or len(rates) == 0:
            logging.error(f"无法从 MT5 获取 {mt5_symbol} 的数据")
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'tick_volume': 'volume', 'time': 'Date'}, inplace=True)
        df.set_index('Date', inplace=True)
        # 保留 OHLCV (Keep OHLCV)
        df = df[['open', 'high', 'low', 'close', 'volume']]
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        return df

    def _get_yf_data(self, symbol, timeframe, n):
        """从 yfinance 获取数据"""
        yf_symbol = self.symbols_map.get(symbol, {}).get('yf', symbol)
        
        # 映射 yfinance 的时间周期
        # yfinance supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        valid_tfs = ['1m', '5m', '15m', '30m', '1h', '1d']
        if timeframe not in valid_tfs:
            timeframe = '1d'
            
        # 根据需要的 K 线数量 n 估算请求的时间范围 period
        period = '1mo'
        if timeframe == '1d':
            period = '1y'
        elif timeframe == '1h':
            period = '3mo'
        elif timeframe in ['1m', '5m', '15m', '30m']:
            period = '5d' # intraday data is limited in yf
            
        try:
            df = yf.download(yf_symbol, period=period, interval=timeframe, progress=False)
            if df.empty:
                logging.warning(f"yfinance 未找到 {yf_symbol} 的数据")
                return pd.DataFrame()
                
            # yfinance 有时返回 MultiIndex 列，需要扁平化处理
            if isinstance(df.columns, pd.MultiIndex):
                # 如果 Ticker 是第 1 层级，则丢弃
                if len(df.columns.levels) > 1:
                     df.columns = df.columns.get_level_values(0)
            
            # 确保列名标准化 (Ensure standard columns)
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            # 检查大小写
            df.columns = [c.capitalize() for c in df.columns]
            
            # 过滤并排序
            df = df[[c for c in required_cols if c in df.columns]]
            
            # 限制返回 n 行
            if len(df) > n:
                df = df.iloc[-n:]
                
            return df
        except Exception as e:
            logging.error(f"获取 {symbol} 的 yfinance 数据时出错: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol):
        """获取当前最新价格"""
        df = self.get_latest_data(symbol, n=1)
        if not df.empty:
            return df['Close'].iloc[-1]
        return 0.0
