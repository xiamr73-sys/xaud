import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

def test_discord_alert():
    if not DISCORD_WEBHOOK_URL:
        print("❌ Error: DISCORD_WEBHOOK_URL not found in environment variables.")
        return

    print(f"🚀 Testing Discord Webhook: {DISCORD_WEBHOOK_URL[:30]}...")
    
    msg = "🤖 **[TEST ALERT]** This is a test message from your Crypto Monitor bot. If you see this, the integration is working!"
    
    try:
        data = {"content": msg}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        
        if response.status_code == 204:
            print("✅ Success! Test message sent to Discord.")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    test_discord_alert()