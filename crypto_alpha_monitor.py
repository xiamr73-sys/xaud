import asyncio
import ccxt.async_support as ccxt
import aiohttp
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ================= Configuration =================
# Discord Webhook URL (Please replace with your actual webhook URL)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1468615311073870149/6ootD_LIjxF14AEbRR5lM3K76CEdk8d7alosYs1oZWHYx58QjjpRQxosbhcYq-X3Q_pk"

# Monitor Settings
CHECK_INTERVAL = 60  # Check every 60 seconds
TOP_N_SYMBOLS = 200   # Number of top symbols to monitor
TIMEFRAME = '1h'     # Timeframe for calculation (1h or 15m)
OI_TIMEFRAME = '1h'  # Timeframe for Open Interest change

# Thresholds
# Long: BTC flat/down, Symbol up, OI up
LONG_BTC_CHANGE_MAX = 0.005   # BTC change < 0.5% (Flat or Down)
LONG_SYMBOL_CHANGE_MIN = 0.01 # Symbol change > 1%
LONG_OI_CHANGE_MIN = 0.03     # OI Increase > 3%

# Short: BTC up, Symbol flat/down, OI up (Divergence)
# OR BTC small drop, Symbol big drop, OI up
SHORT_BTC_CHANGE_MIN = 0.01    # BTC change > 1%
SHORT_SYMBOL_CHANGE_MAX = 0.0  # Symbol change < 0%
SHORT_OI_CHANGE_MIN = 0.03     # OI Increase > 3%

# Excluded Symbols (Stablecoins & Special)
EXCLUDED_COINS = {'USDC', 'USDP', 'TUSD', 'FDUSD', 'DAI', 'BUSD', 'USDT'}

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_alpha.log")
    ]
)
logger = logging.getLogger(__name__)

class CryptoAlphaMonitor:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        self.session = None

    async def setup(self):
        # Load markets to get symbol details
        await self.exchange.load_markets()
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.exchange.close()
        if self.session:
            await self.session.close()

    async def fetch_top_symbols(self) -> List[str]:
        """
        Fetch top 50 symbols by 24h Quote Volume, excluding stablecoins.
        """
        try:
            tickers = await self.exchange.fetch_tickers()
            # Filter for USDT futures
            valid_tickers = []
            for symbol, ticker in tickers.items():
                if '/USDT' in symbol and ticker['quoteVolume'] is not None:
                    base_currency = symbol.split('/')[0]
                    if base_currency not in EXCLUDED_COINS:
                        valid_tickers.append(ticker)
            
            # Sort by quote volume descending
            sorted_tickers = sorted(valid_tickers, key=lambda x: x['quoteVolume'], reverse=True)
            top_symbols = [t['symbol'] for t in sorted_tickers[:TOP_N_SYMBOLS]]
            
            # Ensure BTC/USDT is tracked for benchmark, even if not in top N (unlikely)
            btc_symbol = 'BTC/USDT:USDT'
            if btc_symbol not in top_symbols:
                # Try to find the correct BTC symbol format
                btc_candidates = [s for s in tickers.keys() if 'BTC/USDT' in s]
                if btc_candidates:
                    btc_symbol = btc_candidates[0]
            
            return top_symbols, btc_symbol
        except Exception as e:
            logger.error(f"Error fetching top symbols: {e}")
            return [], None

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch Price OHLCV and Open Interest for a single symbol.
        Returns % Change and OI Change.
        """
        try:
            # Fetch OHLCV for Price Change
            # Fetch 2 candles: [Previous, Current] or [Ago, Current]
            # To get change over last 1h, we need Close of candle 1h ago vs Current Price.
            ohlcv = await self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=2)
            if not ohlcv or len(ohlcv) < 2:
                return None

            # ohlcv: [timestamp, open, high, low, close, volume]
            # Calculate % change from the Open of the current candle (if using 1h candle and it's 30min in, it's 30min change)
            # OR compare Close of previous candle to current Close.
            # Let's use: (Current Close - Open of current candle) / Open of current candle
            # This represents "Change in the current hour"
            # OR (Current Close - Close of previous candle) / Close of previous candle
            
            current_price = ohlcv[-1][4]
            # Use previous candle close as reference base for "Change since last hour close"
            base_price = ohlcv[-2][4] 
            
            price_change_pct = (current_price - base_price) / base_price
            volume_24h = 0 # We might need to fetch ticker for 24h volume if needed, or use ohlcv volume (which is 1h)

            # Fetch Open Interest
            # fetch_open_interest returns current OI
            oi_current_data = await self.exchange.fetch_open_interest(symbol)
            oi_current = float(oi_current_data['openInterestAmount'])

            # Fetch Historical OI to calculate change
            # Note: Not all exchanges support fetch_open_interest_history, but Binance does.
            # We need OI from 1h ago.
            oi_history = await self.exchange.fetch_open_interest_history(symbol, OI_TIMEFRAME, limit=1)
            
            if not oi_history:
                 # Fallback if history not available or empty
                 return None
            
            # oi_history usually returns start of the period.
            oi_prev = float(oi_history[0]['openInterestAmount'])
            
            if oi_prev == 0:
                oi_change_pct = 0
            else:
                oi_change_pct = (oi_current - oi_prev) / oi_prev

            return {
                'symbol': symbol,
                'price': current_price,
                'price_change_pct': price_change_pct,
                'oi_current': oi_current,
                'oi_change_pct': oi_change_pct,
                'volume_24h': 0 # Placeholder, can be filled if we pass ticker info
            }

        except Exception as e:
            # logger.warning(f"Failed to fetch data for {symbol}: {e}")
            return None

    async def analyze_alpha(self):
        """
        Main logic: Compare symbols against BTC and find Alpha.
        """
        logger.info("Starting analysis cycle...")
        
        # 1. Get Symbols
        symbols, btc_symbol = await self.fetch_top_symbols()
        if not symbols or not btc_symbol:
            logger.error("No symbols found.")
            return

        logger.info(f"Monitoring {len(symbols)} symbols. Benchmark: {btc_symbol}")

        # 2. Get BTC Data first (Benchmark)
        btc_data = await self.get_market_data(btc_symbol)
        if not btc_data:
            logger.error("Could not fetch BTC data. Aborting cycle.")
            return
        
        btc_change = btc_data['price_change_pct']
        logger.info(f"BTC Change ({TIMEFRAME}): {btc_change:.2%}")

        # 3. Get Data for all symbols concurrently
        tasks = [self.get_market_data(sym) for sym in symbols if sym != btc_symbol]
        results = await asyncio.gather(*tasks)

        # 4. Filter and Analyze
        for data in results:
            if not data:
                continue

            symbol = data['symbol']
            price_change = data['price_change_pct']
            oi_change = data['oi_change_pct']
            
            # Relative Strength
            rs = price_change - btc_change

            signal_type = None
            reason = ""

            # Strategy 1: Long Signal (Stronger than BTC)
            # Condition: BTC is weak/flat, Symbol is strong, OI increasing
            if (btc_change < LONG_BTC_CHANGE_MAX) and \
               (price_change > LONG_SYMBOL_CHANGE_MIN) and \
               (oi_change > LONG_OI_CHANGE_MIN):
                signal_type = "LONG 🟢"
                reason = f"Strong vs BTC (RS: {rs:.2%}), OI Surge (+{oi_change:.1%})"

            # Strategy 2: Short Signal (Weaker than BTC)
            # Condition: BTC is strong, Symbol is weak, OI increasing (Divergence/Top formation)
            elif (btc_change > SHORT_BTC_CHANGE_MIN) and \
                 (price_change < SHORT_SYMBOL_CHANGE_MAX) and \
                 (oi_change > SHORT_OI_CHANGE_MIN):
                signal_type = "SHORT 🔴"
                reason = f"Weak vs BTC (RS: {rs:.2%}), OI Surge (+{oi_change:.1%})"
            
            # Additional Short Condition: BTC small drop, Symbol big drop (Panic Selling/Breakdown)
            elif (btc_change < 0 and btc_change > -0.01) and \
                 (price_change < -0.02) and \
                 (oi_change > SHORT_OI_CHANGE_MIN):
                 signal_type = "SHORT 🔴"
                 reason = f"Crash vs BTC (RS: {rs:.2%}), OI Surge (+{oi_change:.1%})"

            if signal_type:
                logger.info(f"Signal Found: {symbol} {signal_type}")
                await self.discord_notifier(data, signal_type, reason, rs, btc_change)

    async def discord_notifier(self, data: Dict, signal_type: str, reason: str, rs: float, btc_change: float):
        """
        Send formatted message to Discord.
        """
        if "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
            logger.warning("Discord Webhook not configured. Skipping notification.")
            print(f"[{signal_type}] {data['symbol']} Price: {data['price']} | RS: {rs:.2%} | OI Chg: {data['oi_change_pct']:.2%}")
            return

        embed = {
            "title": f"{signal_type} : {data['symbol']}",
            "color": 5763719 if "LONG" in signal_type else 15548997, # Green or Red
            "fields": [
                {"name": "Price", "value": f"${data['price']}", "inline": True},
                {"name": "Relative Strength", "value": f"{rs:.2%}", "inline": True},
                {"name": "OI Change (1h)", "value": f"📈 {data['oi_change_pct']:.2%}", "inline": True}
            ],
            "footer": {"text": "Crypto Alpha Monitor • By CCXT"}
        }

        payload = {
            "username": "Alpha Hunter",
            "embeds": [embed]
        }

        try:
            async with self.session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 204:
                    logger.error(f"Failed to send Discord notification: {resp.status}")
        except Exception as e:
            logger.error(f"Discord Error: {e}")

    async def run(self):
        """
        Main Loop
        """
        await self.setup()
        logger.info("Bot started. Press Ctrl+C to stop.")
        
        while True:
            try:
                await self.analyze_alpha()
                logger.info(f"Sleeping for {CHECK_INTERVAL}s...")
                await asyncio.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(10) # Wait before retry
        
        await self.close()

if __name__ == "__main__":
    bot = CryptoAlphaMonitor()
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        pass
