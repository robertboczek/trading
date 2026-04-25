"""
Get real-time price quote via the Schwab API.

Usage:
    python schwab_get_price.py TICKER

Requirements:
    pip install schwab-py

Environment variables (or .env file):
    SCHWAB_API_KEY      - your Schwab app key
    SCHWAB_API_SECRET   - your Schwab app secret
    SCHWAB_TOKEN_PATH   - path to the token file (default: conf/schwab/token.json)
"""

import argparse
import os
import sys
import json

import schwab
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def main():
    parser = argparse.ArgumentParser(description="Get real-time price quote from Schwab.")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    api_key = get_env("SCHWAB_API_KEY")
    api_secret = get_env("SCHWAB_API_SECRET")
    token_path = os.environ.get("SCHWAB_TOKEN_PATH", "conf/schwab/token.json")

    # Create authenticated client
    client = schwab.auth.client_from_token_file(token_path, api_key, api_secret)
    
    # Get quote for the ticker
    response = client.get_quote(ticker)

    if response.status_code == 200:
        quote_data = response.json()
        
        if args.json:
            # Output raw JSON
            print(json.dumps(quote_data, indent=2))
        else:
            # Extract and display key information
            if ticker in quote_data:
                quote = quote_data[ticker]['quote']
                
                print(f"\n=== {ticker} Quote ===")
                print(f"Last Price:    ${quote.get('lastPrice', 'N/A'):.2f}" if isinstance(quote.get('lastPrice'), (int, float)) else f"Last Price:    {quote.get('lastPrice', 'N/A')}")
                print(f"Bid Price:     ${quote.get('bidPrice', 'N/A'):.2f}" if isinstance(quote.get('bidPrice'), (int, float)) else f"Bid Price:     {quote.get('bidPrice', 'N/A')}")
                print(f"Ask Price:     ${quote.get('askPrice', 'N/A'):.2f}" if isinstance(quote.get('askPrice'), (int, float)) else f"Ask Price:     {quote.get('askPrice', 'N/A')}")
                print(f"Bid Size:      {quote.get('bidSize', 'N/A')}")
                print(f"Ask Size:      {quote.get('askSize', 'N/A')}")
                print(f"High (Day):    ${quote.get('highPrice', 'N/A'):.2f}" if isinstance(quote.get('highPrice'), (int, float)) else f"High (Day):    {quote.get('highPrice', 'N/A')}")
                print(f"Low (Day):     ${quote.get('lowPrice', 'N/A'):.2f}" if isinstance(quote.get('lowPrice'), (int, float)) else f"Low (Day):     {quote.get('lowPrice', 'N/A')}")
                print(f"Volume:        {quote.get('totalVolume', 'N/A'):,}" if isinstance(quote.get('totalVolume'), (int, float)) else f"Volume:        {quote.get('totalVolume', 'N/A')}")
                print(f"Open Price:    ${quote.get('openPrice', 'N/A'):.2f}" if isinstance(quote.get('openPrice'), (int, float)) else f"Open Price:    {quote.get('openPrice', 'N/A')}")
                print(f"Close Price:   ${quote.get('closePrice', 'N/A'):.2f}" if isinstance(quote.get('closePrice'), (int, float)) else f"Close Price:   {quote.get('closePrice', 'N/A')}")
                print(f"Net Change:    ${quote.get('netChange', 'N/A'):.2f}" if isinstance(quote.get('netChange'), (int, float)) else f"Net Change:    {quote.get('netChange', 'N/A')}")
                print(f"% Change:      {quote.get('netPercentChange', 'N/A'):.2f}%" if isinstance(quote.get('netPercentChange'), (int, float)) else f"% Change:      {quote.get('netPercentChange', 'N/A')}")
                print()
            else:
                print(f"Error: No quote data found for {ticker}", file=sys.stderr)
                sys.exit(1)
    else:
        print(f"Error retrieving quote. Status: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()