# -*- coding: utf-8 -*-
import os
import ccxt.async_support as ccxt
from dotenv import load_dotenv
from loguru import logger

# 加载环境变量
load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

# 检查 API Key 配置
if not BINANCE_API_KEY or not BINANCE_SECRET:
    logger.warning("未在 .env 文件中找到 BINANCE_API_KEY 或 BINANCE_SECRET，部分功能可能受限。")

# Discord 配置
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

async def get_exchange():
    """
    创建并配置 Binance 异步交易所实例 (Futures)
    
    Returns:
        ccxt.binance: 配置好的 Binance 交易所实例
    """
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,  # 启用内置的速率限制处理
        'options': {
            'defaultType': 'future',  # 默认连接到合约市场 (USDT-M)
        }
    })
    
    return exchange
