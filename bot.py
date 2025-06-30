import os
import time
from binance.client import Client
from dotenv import load_dotenv

print("🟢 Starting Binance bot...")

# Load environment variables
load_dotenv()

# Initialize Binance client
try:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    client = Client(api_key, api_secret)

    account_info = client.get_margin_account()
    usdt_balance = next((a for a in account_info['userAssets'] if a['asset'] == 'USDT'), None)
    
    if usdt_balance:
        print(f"💰 Free USDT: {usdt_balance['free']}")
    else:
        print("⚠️ USDT balance not found.")

except Exception as e:
    print(f"❌ Error connecting to Binance: {e}")

# Idle loop to keep the bot alive
while True:
    print("⏳ Bot running...")
    time.sleep(30)
