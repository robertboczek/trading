import numpy as np
import sys
import argparse
import yfinance as yf
print(np.__version__)

parser = argparse.ArgumentParser(description="A simple script")
parser.add_argument("ticker", help="The ticker symbol of the stock to download")

msg = "Roll a dice!"
print(msg)

args = parser.parse_args()
ticker = args.ticker

intra_day = yf.download(ticker, start='2026-04-09', end='2026-04-10', interval='1m')
print(intra_day.size)

intra_day.to_csv(f'trading/data/{ticker}/4_10_26.csv', index=True)
