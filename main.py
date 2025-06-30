import os
from binance.client import Client
from dotenv import load_dotenv

# Load .env file for API credentials
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)

def check_account():
    try:
        account = client.get_margin_account()
        print("Connected to Binance Margin Trading.")
        print(f"Available USDT: {account['totalAssetOfBtc']}")
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    check_account()
