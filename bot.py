import os
import time
from binance.client import Client
from dotenv import load_dotenv

print("🟢 Step 1: Script started")

# Load environment variables
load_dotenv()
print("🟢 Step 2: Loaded .env")

# Initialize Binance client
try:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    print("🟢 Step 3: Got API keys")

    client = Client(api_key, api_secret)
    print("🟢 Step 4: Binance client initialized")

    account_info = client.get_margin_account()
    print("🟢 Step 5: Retrieved margin account")

    usdt_balance = next((a for a in account_info['userAssets'] if a['asset'] == 'USDT'), None)
    
    if usdt_balance:
        print(f"💰 Free USDT: {usdt_balance['free']}")
    else:
        print("⚠️ USDT balance not found.")

except Exception as e:
    print(f"❌ Error connecting to Binance: {e}")

print("🟢 Step 6: Entering main loop")

while True:
    print("⏳ Heartbeat — bot running...")
    time.sleep(30)
