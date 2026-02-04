import asyncio
import aiohttp
from crypto_alpha_monitor import DISCORD_WEBHOOK_URL

async def send_test():
    print(f"Testing Webhook: {DISCORD_WEBHOOK_URL}")
    
    embed = {
        "title": "🛠️ Debug Test Message",
        "description": "This is a test message to verify Discord Webhook configuration.",
        "color": 3447003, # Blue
        "fields": [
            {"name": "Status", "value": "Active", "inline": True},
            {"name": "Message", "value": "Connection successful! 🚀", "inline": True}
        ],
        "footer": {"text": "Crypto Alpha Monitor Debugger"}
    }

    payload = {
        "username": "Alpha Monitor Debugger",
        "embeds": [embed]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status in [200, 204]:
                    print("✅ Test message sent successfully! Please check your Discord channel.")
                else:
                    print(f"❌ Failed to send message. Status: {resp.status}")
                    print(await resp.text())
        except Exception as e:
            print(f"❌ Error sending message: {e}")

if __name__ == "__main__":
    try:
        if "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
            print("❌ Error: Webhook URL is not configured in crypto_alpha_monitor.py")
        else:
            asyncio.run(send_test())
    except KeyboardInterrupt:
        pass
