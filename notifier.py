import requests
import logging

# Webhook URL from crypto_alpha_monitor.py
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1468615311073870149/6ootD_LIjxF14AEbRR5lM3K76CEdk8d7alosYs1oZWHYx58QjjpRQxosbhcYq-X3Q_pk"

def send_discord_alert(signal_data):
    """
    Send a trade signal to Discord via Webhook.
    signal_data: dict containing signal details (symbol, signal, price, sl, tp, reason, etc.)
    """
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        logging.warning("Discord Webhook URL is not configured.")
        return

    signal_type = signal_data.get('signal')
    symbol = signal_data.get('symbol')
    price = signal_data.get('price')
    sl = signal_data.get('sl')
    tp = signal_data.get('tp')
    rr = signal_data.get('rr')
    reason = signal_data.get('reason')
    
    # Color: Green for BUY, Red for SELL
    color = 5763719 if signal_type == 'BUY' else 15548997
    
    emoji = "🟢" if signal_type == 'BUY' else "🔴"

    embed = {
        "title": f"{emoji} 新信号触发: {symbol} {signal_type}",
        "description": f"**策略理由:** {reason}",
        "color": color,
        "fields": [
            {"name": "入场价格", "value": f"{price:.2f}", "inline": True},
            {"name": "止损位 (SL)", "value": f"{sl:.2f}", "inline": True},
            {"name": "止盈位 (TP)", "value": f"{tp:.2f}", "inline": True},
            {"name": "盈亏比 (RR)", "value": f"{rr:.2f}", "inline": True}
        ],
        "footer": {"text": "量化监控系统"}
    }

    payload = {
        "username": "量化信号机器人",
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logging.info(f"Discord notification sent for {symbol} {signal_type}")
    except Exception as e:
        logging.error(f"Failed to send Discord notification: {e}")

def send_trade_close_alert(trade_data):
    """
    Send a trade close alert (TP/SL Hit).
    """
    if not DISCORD_WEBHOOK_URL:
        return

    symbol = trade_data.get('symbol')
    result_type = trade_data.get('result') # 'Take Profit' or 'Stop Loss'
    pnl = trade_data.get('pnl', 0)
    exit_price = trade_data.get('exit_price')
    
    emoji = "💰" if result_type == 'Take Profit' else "🛡️"
    color = 5763719 if result_type == 'Take Profit' else 15548997
    
    embed = {
        "title": f"{emoji} 交易结束: {symbol}",
        "description": f"**触发:** {result_type}",
        "color": color,
        "fields": [
            {"name": "平仓价格", "value": f"{exit_price:.2f}", "inline": True},
            {"name": "预计盈亏", "value": f"{pnl:.2f}", "inline": True}
        ],
        "footer": {"text": "量化监控系统 - 自动风控"}
    }
    
    payload = {
        "username": "量化风控机器人",
        "embeds": [embed]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception:
        pass
