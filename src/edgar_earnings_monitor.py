"""
EDGAR Earnings Monitor
Polls SEC EDGAR RSS feed for new 8-K filings (earnings press releases).
Usage:
    python edgar_earnings_monitor.py                        # monitor all companies
    python edgar_earnings_monitor.py --tickers META AAPL MSFT  # watch specific tickers
    python edgar_earnings_monitor.py --interval 60          # poll every 60 seconds
"""

import argparse
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

import requests

# SEC requires a User-Agent header identifying your app
HEADERS = {
    "User-Agent": "EarningsMonitor trading-bot@example.com",
    "Accept-Encoding": "gzip, deflate",
}

EDGAR_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_COMPANY_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=8-K&dateRange=custom&startdt={date}"


@dataclass
class Filing:
    company: str
    cik: str
    filed_at: str
    filing_url: str
    accession: str


def fetch_recent_8k_filings() -> list[Filing]:
    """Fetch the latest 8-K filings from EDGAR RSS feed."""
    resp = requests.get(EDGAR_RSS_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.content)
    filings = []

    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)
        link_el = entry.find("atom:link", ns)
        url = link_el.attrib.get("href", "") if link_el is not None else ""

        # Extract CIK and accession from the URL
        # URL format: .../cgi-bin/browse-edgar?action=getcompany&CIK=XXXXXXXX&...
        cik = ""
        accession = ""
        if "CIK=" in url:
            cik = url.split("CIK=")[1].split("&")[0]

        company = title.split(" - ")[0].strip() if " - " in title else title

        filings.append(Filing(
            company=company,
            cik=cik,
            filed_at=updated,
            filing_url=url,
            accession=accession,
        ))

    return filings


def get_cik_for_ticker(ticker: str) -> str | None:
    """Look up CIK number for a given ticker symbol."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=8-K"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])
    if hits:
        return hits[0].get("_source", {}).get("entity_id", "")
    return None


def get_latest_filings_for_ticker(ticker: str, since_date: str) -> list[dict]:
    """Fetch latest 8-K filings for a specific ticker using full-text search."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=8-K&dateRange=custom&startdt={since_date}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        src = hit.get("_source", {})
        results.append({
            "company": src.get("display_names", [ticker])[0] if src.get("display_names") else ticker,
            "filed_at": src.get("file_date", ""),
            "accession": src.get("file_num", ""),
            "form": src.get("form_type", "8-K"),
            "url": f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id', '')}/{src.get('file_date', '').replace('-', '')}/",
        })
    return results


def print_filing(filing: Filing, label: str = "NEW") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{label}] {filing.company}")
    print(f"         Filed: {filing.filed_at}")
    print(f"         URL:   {filing.filing_url}")
    print()


def monitor_all(interval: int) -> None:
    """Poll EDGAR RSS for all new 8-K filings."""
    print(f"Monitoring all 8-K filings, polling every {interval}s. Ctrl+C to stop.\n")
    seen: set[str] = set()

    while True:
        try:
            filings = fetch_recent_8k_filings()
            for f in filings:
                key = f"{f.cik}_{f.filed_at}"
                if key not in seen:
                    seen.add(key)
                    print_filing(f, label="8-K")
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch filings: {e}")
        except ET.ParseError as e:
            print(f"[ERROR] Failed to parse RSS feed: {e}")

        time.sleep(interval)


def monitor_tickers(tickers: list[str], interval: int) -> None:
    """Poll EDGAR for 8-K filings from specific tickers."""
    print(f"Monitoring tickers: {', '.join(tickers)} — polling every {interval}s. Ctrl+C to stop.\n")
    seen: set[str] = set()
    today = datetime.now().strftime("%Y-%m-%d")

    while True:
        for ticker in tickers:
            try:
                filings = get_latest_filings_for_ticker(ticker, since_date=today)
                for f in filings:
                    key = f"{ticker}_{f['filed_at']}_{f['accession']}"
                    if key not in seen:
                        seen.add(key)
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] [8-K] {f['company']} ({ticker})")
                        print(f"         Filed: {f['filed_at']}")
                        print(f"         Form:  {f['form']}")
                        print(f"         URL:   {f['url']}")
                        print()
            except requests.RequestException as e:
                print(f"[ERROR] {ticker}: {e}")

        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor SEC EDGAR for new 8-K earnings filings")
    parser.add_argument(
        "--tickers", nargs="+", metavar="TICKER",
        help="Watch specific ticker symbols (e.g. META AAPL MSFT). Omit to monitor all."
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Polling interval in seconds (default: 60)"
    )
    args = parser.parse_args()

    if args.tickers:
        monitor_tickers([t.upper() for t in args.tickers], args.interval)
    else:
        monitor_all(args.interval)


if __name__ == "__main__":
    main()
