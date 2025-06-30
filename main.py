import os
from binance.client import Client
from dotenv import load_dotenv

# Load API credentials from environment
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Connect to Binance Margin account
client = Client(API_KEY, API_SECRET)

def show_margin_status():
    try:
        account = client.get_margin_account()

        # Find USDT balances in the margin account
        for asset in account['userAssets']:
            if asset['asset'] == 'USDT':
                free = float(asset['free'])
                borrowable = float(asset['borrowable'])
                net_asset = float(asset['netAsset'])

                print("✅ Connected to Binance Margin account.")
                print(f"Available USDT: {free}")
                print(f"Borrowable USDT: {borrowable}")
                print(f"Net USDT Equity: {net_asset}")
                return

        print("USDT asset not found in margin account.")
    except Exception as e:
        print("❌ Error connecting to Binance:", e)

if __name__ == "__main__":
    show_margin_status()
