"""
Place a market buy order via the Schwab API.

Usage:
    python trader.py TICKER [--quantity N]


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
from pydoc import doc
import sys
import json

from datetime import datetime
import time
from urllib import response
from urllib import response
import fitz
import requests  # PyMuPDF

import trader_util

from dotenv import load_dotenv

from trader_util import get_env, print_time, sleep_until, get_headers

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Get real-time price quote from Schwab.")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    api_key = get_env("SCHWAB_API_KEY")
    api_secret = get_env("SCHWAB_API_SECRET")
    token_path = os.environ.get("SCHWAB_TOKEN_PATH", "conf/schwab/token.json")

    print_time()

    with open(f'stock/{ticker}.json', 'r') as file:
        data = json.load(file)
    earnings_date_str = data.get("earnings_date")
    earnings_time_str = data.get("earnings_time")
    earnings_url = data.get("earnings_website")
    print(f"Earnings date: {earnings_date_str} {earnings_time_str}")
    print(f"Earnings website: {earnings_url}")

    accept = data.get("accept", "html")
    expectations_doc = data.get("expectations_doc")
    earnings_doc = data.get("earnings_doc")

    doc = fitz.open(expectations_doc)
    expectation_content = ""
    for page in doc:
        expectation_content += page.get_text()

    #print(expectation_content)

    headers = get_headers(accept_type=accept)

    #time.sleep(100)

    target = datetime.now().replace(day=24, hour=3, minute=59, second=00, microsecond=0)
    #sleep_until(target)

    # keep retrying every 5 seconds 
    report_ready = False
    response = None
    print(earnings_url)
    print(headers)
    while not report_ready:
        print_time()
        response = requests.get(earnings_url, headers=headers)
        if response.status_code == 200:
            if response.content.__contains__(b"CAN'T FIND WHAT YOU'RE LOOKING FOR?"):
                print("Report not ready yet. Retrying...")
                report_ready = False
            else:
                print("Report ready")
                report_ready = True
        else:
            print(f"Failed to download file (status code: {response.status_code}). Retrying...")
            time.sleep(5)

    print(response.status_code)

    with open(earnings_doc, "wb") as f:
        f.write(response.content)

    doc = fitz.open(earnings_doc)
    earnings_report_content = ""
    for page in doc:
        earnings_report_content += page.get_text()

    # print(earnings_report_content)

    print_time()

    message = trader_util.query_claude(ticker, expectation_content, earnings_report_content)
    print(fitz.message.content[0].text)
    print_time()
    result_string = fitz.message.content[0].text[0:20]  # get first 20 characters to check for bullish/bearish/neutral
    if (result_string.lower().__contains__("bullish")):
        print("Stock will likely go up, consider buying or holding.")

    elif (result_string.lower().__contains__("bearish")):
        print("Stock will likely go down, consider selling or shorting.")

    print_time()


if __name__ == "__main__":
    main()
