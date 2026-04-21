"""
Place a market buy order via the Schwab API.

Usage:
    python schwab_buy_order.py TICKER [--quantity N] [--dry-run]

Requirements:
    pip install schwab-py

Environment variables (or .env file):
    SCHWAB_API_KEY      - your Schwab app key
    SCHWAB_API_SECRET   - your Schwab app secret
    SCHWAB_ACCOUNT_HASH - your encrypted account number (see note below)
    SCHWAB_TOKEN_PATH   - path to the token file (default: token.json)

To get SCHWAB_ACCOUNT_HASH, run this once after authenticating:
    python -c "import schwab, os; c = schwab.auth.client_from_token_file(os.environ['SCHWAB_TOKEN_PATH'], os.environ['SCHWAB_API_KEY'], os.environ['SCHWAB_API_SECRET']); [print(a['hashValue'], a['accountNumber']) for a in c.get_account_numbers().json()]"
"""

import argparse
import os
import sys

import schwab
from schwab.auth import easy_client
from schwab.orders.equities import equity_buy_market
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def main():
    parser = argparse.ArgumentParser(description="Place a Schwab market buy order.")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--quantity", type=int, default=1, help="Number of shares to buy (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Print the order spec without submitting")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    quantity = args.quantity

    if quantity <= 0:
        print("Error: quantity must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    api_key = get_env("SCHWAB_API_KEY")
    api_secret = get_env("SCHWAB_API_SECRET")
    account_hash = get_env("SCHWAB_ACCOUNT_HASH")
    token_path = os.environ.get("SCHWAB_TOKEN_PATH", "conf/schwab/token.json")

    order = equity_buy_market(ticker, quantity)

    if args.dry_run:
        print(f"[dry-run] Would place market BUY order: {quantity} x {ticker}")
        print(f"Order spec: {order.build()}")
        return
    
    #print(api_key, api_secret, token_path)
    # client = easy_client(
    #     api_key=api_key,
    #     app_secret=api_secret,
    #     callback_url='https://127.0.0.1:8080',
    #     token_path=token_path
    # )

    client = schwab.auth.client_from_token_file(token_path, api_key, api_secret)
    resp = client.get_account_numbers()
    print(f"Available accounts: {resp.json()}")

    response = client.place_order(account_hash, order)

    if response.status_code == 201:
        order_id = response.headers.get("Location", "").split("/")[-1]
        print(f"Order placed successfully. Order ID: {order_id}")
    else:
        print(f"Order failed. Status: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
