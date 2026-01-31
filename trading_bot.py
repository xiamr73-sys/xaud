import os
import time
import requests
import ccxt
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
API_URL = "http://127.0.0.1:5001/api/data"  # URL of the monitor app
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')

# Trading Settings
DRY_RUN = True  # Set to False to execute real trades
MAX_OPEN_POSITIONS = 3
LEVERAGE = 5
USDT_PER_TRADE = 20.0  # Amount of USDT to use per trade

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        try:
            logger.info("Loading markets from Binance...")
            self.exchange.load_markets()
            logger.info("Markets loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            
        self.open_positions = []
        
        if DRY_RUN:
            logger.warning("⚠️  DRY RUN MODE ENABLED. No real trades will be executed.")
        else:
            logger.warning("🚨  REAL TRADING MODE ENABLED. Real funds are at risk.")

    def get_signals(self):
        """Fetch analysis data from the local monitor API."""
        try:
            response = requests.get(API_URL)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch signals: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error connecting to monitor API: {e}")
            return None

    def get_current_positions(self):
        """Fetch current open positions from Binance."""
        if DRY_RUN:
            # In Dry Run, we just track what we 'opened' in memory (simplified)
            # Or we can just return empty and rely on logic to not duplicate based on logs?
            # Better: In Dry Run, we don't check exchange positions.
            return self.open_positions
        
        try:
            positions = self.exchange.fetch_positions()
            # Filter for positions with size > 0
            active_positions = [p for p in positions if float(p['contracts']) > 0]
            return [p['symbol'] for p in active_positions]
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def set_leverage(self, symbol):
        if DRY_RUN:
            return True
        try:
            self.exchange.set_leverage(LEVERAGE, symbol)
            return True
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")
            return False

    def place_order(self, symbol, side, entry_price, sl_price, tp_price):
        """
        Executes the trade:
        1. Market Entry
        2. Stop Loss Order
        3. Take Profit Order
        """
        if symbol in self.open_positions:
            logger.info(f"Skipping {symbol}, already in local position list.")
            return

        # Calculate Quantity
        # Quantity = USDT_PER_TRADE / Entry Price
        amount = USDT_PER_TRADE / entry_price
        
        # Adjust precision (step size)
        try:
            if not self.exchange.markets:
                if DRY_RUN:
                     logger.warning(f"Markets not loaded. Using raw amount for {symbol} in DRY_RUN.")
                else:
                     logger.error(f"Markets not loaded. Cannot execute trade for {symbol}.")
                     return
            else:
                amount = self.exchange.amount_to_precision(symbol, amount)
        except Exception as e:
            logger.error(f"Error getting market info for {symbol}: {e}")
            if not DRY_RUN:
                return

        logger.info(f"🚀 Signal Found: {side} {symbol} @ {entry_price}")
        logger.info(f"   TP: {tp_price}, SL: {sl_price}, Amount: {amount}")

        if DRY_RUN:
            logger.info(f"   [DRY RUN] Would execute: Market {side} {amount} {symbol}")
            self.open_positions.append(symbol)
            return

        # Execute Real Trade
        try:
            # 1. Set Leverage
            self.set_leverage(symbol)

            # 2. Market Entry
            order = self.exchange.create_order(symbol, 'market', side, amount)
            logger.info(f"   ✅ Entry Order Filled: {order['id']}")
            self.open_positions.append(symbol) # Track locally too

            # 3. Place TP/SL
            # Binance Futures allows placing TP/SL as separate orders or with the position.
            # Usually STOP_MARKET and TAKE_PROFIT_MARKET orders are used.
            
            # Determine logic based on side
            sl_side = 'sell' if side == 'buy' else 'buy'
            tp_side = 'sell' if side == 'buy' else 'buy'

            # Stop Loss
            self.exchange.create_order(symbol, 'STOP_MARKET', sl_side, amount, params={
                'stopPrice': sl_price,
                'reduceOnly': True
            })
            logger.info(f"   🛡️ Stop Loss Placed @ {sl_price}")

            # Take Profit
            self.exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', tp_side, amount, params={
                'stopPrice': tp_price,
                'reduceOnly': True
            })
            logger.info(f"   💰 Take Profit Placed @ {tp_price}")

        except Exception as e:
            logger.error(f"❌ Trade Execution Failed for {symbol}: {e}")

    def run(self):
        logger.info("🤖 Quantitative Trading Bot Started...")
        logger.info(f"   Mode: {'DRY RUN' if DRY_RUN else 'REAL TRADING'}")
        logger.info(f"   Monitoring: {API_URL}")
        
        while True:
            try:
                # 1. Get Data
                data = self.get_signals()
                if not data:
                    time.sleep(60)
                    continue

                # 2. Get Current Positions (Real or Simulated)
                # For real trading, we should re-fetch from exchange to be accurate
                if not DRY_RUN:
                    current_symbols = self.get_current_positions()
                    # Update local list
                    self.open_positions = current_symbols
                
                # Check limits
                if len(self.open_positions) >= MAX_OPEN_POSITIONS:
                    logger.info(f"Max positions reached ({len(self.open_positions)}/{MAX_OPEN_POSITIONS}). Waiting...")
                    time.sleep(300)
                    continue

                # 3. Analyze Longs
                longs = data.get('longs', [])
                for coin in longs:
                    symbol = coin['symbol']
                    # Clean symbol (e.g. FIDA/USDT:USDT -> FIDA/USDT)
                    # CCXT expects 'BTC/USDT' usually, but 'FIDA/USDT:USDT' is fine for some exchange mappings.
                    # Let's check what monitor returns. It returns whatever CCXT uses.
                    # If monitor uses 'FIDA/USDT:USDT', we should use that.
                    
                    if symbol not in self.open_positions:
                        # Validate data
                        tp = coin.get('tp_price', 0)
                        sl = coin.get('sl_price', 0)
                        price = coin.get('close', 0)
                        
                        if tp > 0 and sl > 0 and price > 0:
                            self.place_order(symbol, 'buy', price, sl, tp)
                            if len(self.open_positions) >= MAX_OPEN_POSITIONS:
                                break
                
                # 4. Analyze Shorts
                if len(self.open_positions) < MAX_OPEN_POSITIONS:
                    shorts = data.get('shorts', [])
                    for coin in shorts:
                        symbol = coin['symbol']
                        if symbol not in self.open_positions:
                            tp = coin.get('tp_price', 0)
                            sl = coin.get('sl_price', 0)
                            price = coin.get('close', 0)
                            
                            if tp > 0 and sl > 0 and price > 0:
                                self.place_order(symbol, 'sell', price, sl, tp)
                                if len(self.open_positions) >= MAX_OPEN_POSITIONS:
                                    break

                logger.info("Cycle completed. Waiting 5 minutes...")
                time.sleep(300) # Wait 5 minutes before next check

            except KeyboardInterrupt:
                logger.info("Bot stopped by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
