import numpy as np
import sys
import argparse
import yfinance as yf
from datetime import datetime, timedelta
import os

print(np.__version__)

parser = argparse.ArgumentParser(description="Download 1m interval stock data for the last 30 days")
parser.add_argument("ticker", help="The ticker symbol of the stock to download")

args = parser.parse_args()
ticker = args.ticker

# Create directory for ticker if it doesn't exist
ticker_dir = f'trading/data/{ticker}'
os.makedirs(ticker_dir, exist_ok=True)

# Calculate date range (last 30 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

print(f"Downloading {ticker} data from {start_date.date()} to {end_date.date()}")

# Loop through each day
current_date = start_date
while current_date <= end_date:
    # Format dates for yfinance
    date_str = current_date.strftime('%Y-%m-%d')
    
    # Format filename as mm_dd_year.csv
    filename = current_date.strftime('%m_%d_%y.csv')
    filepath = f'{ticker_dir}/{filename}'
    
    try:
        next_day = current_date + timedelta(days=1)
        # Download 1m interval data for the specific day
        intra_day = yf.download(ticker, start=date_str, end=next_day, interval='1m', progress=False)
        
        if not intra_day.empty:
            intra_day.to_csv(filepath, index=True)
            print(f"Saved {date_str}: {intra_day.shape[0]} records to {filepath}")
        else:
            print(f"No data for {date_str} (market closed or no trading)")
    except Exception as e:
        print(f"Error downloading data for {date_str}: {e}")
    
    # Move to next day
    current_date += timedelta(days=1)

print(f"\nCompleted downloading data for {ticker}")
