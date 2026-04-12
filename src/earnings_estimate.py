import argparse
import yfinance as yf
import pandas as pd


def get_earnings_info(ticker: str) -> None:
    t = yf.Ticker(ticker)

    # Upcoming earnings date
    calendar = t.calendar
    earnings_date = None
    if calendar is not None and "Earnings Date" in calendar:
        earnings_date = calendar["Earnings Date"]
        if isinstance(earnings_date, list):
            earnings_date = earnings_date[0]

    # EPS and Revenue estimates (next quarter)
    eps_estimate = None
    revenue_estimate = None

    earnings_estimate = t.earnings_estimate
    revenue_estimate_df = t.revenue_estimate

    if earnings_estimate is not None and not earnings_estimate.empty:
        if "0q" in earnings_estimate.index:
            row = earnings_estimate.loc["0q"]
            eps_estimate = row.get("avg")

    if revenue_estimate_df is not None and not revenue_estimate_df.empty:
        if "0q" in revenue_estimate_df.index:
            row = revenue_estimate_df.loc["0q"]
            revenue_estimate = row.get("avg")

    print(f"\nEarnings info for {ticker.upper()}")
    print("-" * 40)
    print(f"Upcoming earnings date : {earnings_date if earnings_date else 'N/A'}")
    print(f"Expected EPS (next qtr): {eps_estimate if eps_estimate is not None else 'N/A'}")

    if revenue_estimate is not None:
        print(f"Expected Revenue       : ${revenue_estimate:,.0f}")
    else:
        print(f"Expected Revenue       : N/A")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get expected EPS, Revenue, and upcoming earnings date for a ticker")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    args = parser.parse_args()

    get_earnings_info(args.ticker)
