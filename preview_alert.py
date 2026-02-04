import asyncio
import aiohttp
from crypto_alpha_monitor import DISCORD_WEBHOOK_URL

async def send_preview_alerts():
    print("🚀 Sending Preview Alerts to Discord...")

    async with aiohttp.ClientSession() as session:
        # 1. Simulate LONG Signal
        long_data = {
            'symbol': 'ETH/USDT:USDT',
            'price': 3542.10,
            'oi_change_pct': 0.085, # +8.5%
        }
        long_rs = 0.042
        long_btc_change = -0.005
        long_reason = f"Strong vs BTC (RS: {long_rs:.2%}), OI Surge (+{long_data['oi_change_pct']:.1%})"
        
        await send_mock_alert(session, long_data, "LONG 🟢", long_reason, long_rs, long_btc_change)

        # 2. Simulate SHORT Signal
        short_data = {
            'symbol': 'SOL/USDT:USDT',
            'price': 148.50,
            'oi_change_pct': 0.062, # +6.2%
        }
        short_rs = -0.051
        short_btc_change = 0.015
        short_reason = f"Weak vs BTC (RS: {short_rs:.2%}), OI Surge (+{short_data['oi_change_pct']:.1%})"
        
        await send_mock_alert(session, short_data, "SHORT 🔴", short_reason, short_rs, short_btc_change)

async def send_mock_alert(session, data, signal_type, reason, rs, btc_change):
    embed = {
        "title": f"{signal_type} : {data['symbol']}",
        "color": 5763719 if "LONG" in signal_type else 15548997, # Green or Red
        "fields": [
            {"name": "Price", "value": f"${data['price']}", "inline": True},
            {"name": "Relative Strength", "value": f"{rs:.2%}", "inline": True},
            {"name": "OI Change (1h)", "value": f"📈 {data['oi_change_pct']:.2%}", "inline": True}
        ],
        "footer": {"text": "Crypto Alpha Monitor • PREVIEW MODE"}
    }

    payload = {
        "username": "Alpha Hunter",
        "embeds": [embed]
    }

    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
            if resp.status == 204:
                print(f"✅ Sent {signal_type} alert successfully.")
            else:
                print(f"❌ Failed to send {signal_type} alert. Status: {resp.status}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        print("❌ Webhook not configured.")
    else:
        asyncio.run(send_preview_alerts())
