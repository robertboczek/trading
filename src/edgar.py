import time
import re
import requests
from datetime import datetime

# ----------------------------
# CONFIG
# ----------------------------
RSS_URL = "https://www.businesswire.com/portal/site/home/template.PAGE/rss/?rssfeed=G1QFDERJXkJeEFJQV1ZQFFZRUw=="
HEADERS = {
    "User-Agent": "earnings-bot your_email@example.com"
}
POLL_INTERVAL = 5  # seconds

seen_links = set()


# ----------------------------
# HELPERS
# ----------------------------
def extract_ticker(title):
    """
    Extract ticker from headline like:
    'Tesla, Inc. (TSLA) Reports Q1 Results'
    """
    match = re.search(r"\(([A-Z]{1,5})\)", title)
    return match.group(1) if match else None


def get_cik_from_ticker(ticker):
    """
    Map ticker -> CIK using SEC mapping
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    data = requests.get(url, headers=HEADERS).json()

    for entry in data.values():
        if entry["ticker"].upper() == ticker:
            return str(entry["cik_str"]).zfill(10)
    return None


def get_latest_8k(cik):
    """
    Get latest 8-K filing metadata
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS).json()

    filings = data["filings"]["recent"]

    for i, form in enumerate(filings["form"]):
        if form == "8-K":
            return {
                "accession": filings["accessionNumber"][i].replace("-", ""),
                "primary_doc": filings["primaryDocument"][i],
                "date": filings["filingDate"][i]
            }
    return None


def get_8k_url(cik, accession, primary_doc):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"


# ----------------------------
# CORE LOOP
# ----------------------------
def monitor():
    print("Starting earnings monitor...\n")

    while True:
        ticker = "TSLA"
        if not ticker:
            print("No ticker found, skipping.")
            continue

        print(f"Detected ticker: {ticker}")

        cik = get_cik_from_ticker(ticker)

        if not cik:
            print("CIK not found.")
            continue

        filing = get_latest_8k(cik)

        if not filing:
            print("No 8-K found.")
            continue

        url = get_8k_url(cik, filing["accession"], filing["primary_doc"])

        print("🚀 8-K FOUND:")
        print(f"Ticker: {ticker}")
        print(f"Filed: {filing['date']}")
        print(f"URL: {url}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    monitor()