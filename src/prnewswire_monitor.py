"""
PR Newswire Earnings Monitor
Monitors PR Newswire RSS feed for earnings press releases — typically 10-15 min
faster than EDGAR 8-K filings appearing on SEC.gov.

Usage:
    python prnewswire_monitor.py                            # monitor all earnings releases
    python prnewswire_monitor.py --tickers META AAPL MSFT  # filter by company name/ticker
    python prnewswire_monitor.py --interval 30             # poll every 30 seconds
"""

import argparse
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EarningsMonitor/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}

# PR Newswire RSS feeds
FEEDS = {
    "all":      "https://www.prnewswire.com/rss/news-releases-list.rss",
    "finance":  "https://www.prnewswire.com/rss/financial-news.rss",
    "earnings": "https://www.prnewswire.com/rss/financial-news.rss",
}

# Keywords that strongly indicate an earnings/financial results release
EARNINGS_KEYWORDS = [
    "fourth quarter",
    "third quarter",
    "second quarter",
    "first quarter",
    "q4 2",
    "q3 2",
    "q2 2",
    "q1 2",
    "full year results",
    "full-year results",
    "annual results",
    "financial results",
    "earnings results",
    "reports results",
    "quarterly results",
    "quarterly earnings",
    "net income",
    "revenue of $",
    "eps of",
]

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "prn":   "http://www.prnewswire.com/rss/prn",
    "dc":    "http://purl.org/dc/elements/1.1/",
}


@dataclass
class Release:
    title: str
    link: str
    pub_date: str
    description: str
    subjects: list[str]
    contributor: str  # company name from dc:contributor


def is_earnings_release(release: Release) -> bool:
    """Return True if the release looks like an earnings report."""
    text = (release.title + " " + release.description).lower()
    return any(kw in text for kw in EARNINGS_KEYWORDS)


def matches_ticker_filter(release: Release, tickers: list[str]) -> bool:
    """Return True if release mentions any of the given ticker symbols or company names."""
    text = (release.title + " " + release.description + " " + release.contributor).upper()
    return any(t.upper() in text for t in tickers)


def fetch_feed(url: str) -> list[Release]:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    if channel is None:
        return []

    releases = []
    for item in channel.findall("item"):
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        description = item.findtext("description", default="").strip()

        # Strip CDATA artifacts
        for tag in ("<![CDATA[", "]]>"):
            description = description.replace(tag, "")

        subjects = [el.text for el in item.findall("prn:subject", NS) if el.text]
        contributor = item.findtext("dc:contributor", default="", namespaces=NS).strip()

        releases.append(Release(
            title=title,
            link=link,
            pub_date=pub_date,
            description=description,
            subjects=subjects,
            contributor=contributor,
        ))

    return releases


def format_pub_date(pub_date: str) -> str:
    try:
        dt = parsedate_to_datetime(pub_date)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return pub_date


def print_release(release: Release) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {release.title}")
    if release.contributor:
        print(f"         Company:   {release.contributor}")
    print(f"         Published: {format_pub_date(release.pub_date)}")
    print(f"         URL:       {release.link}")
    if release.description:
        snippet = release.description[:200].strip()
        if len(release.description) > 200:
            snippet += "..."
        print(f"         Snippet:   {snippet}")
    print()


def monitor(tickers: list[str], interval: int, feed_url: str) -> None:
    ticker_info = f" | watching: {', '.join(tickers)}" if tickers else " | watching: all companies"
    print(f"PR Newswire Earnings Monitor — polling every {interval}s{ticker_info}")
    print(f"Feed: {feed_url}\n")

    seen: set[str] = set()
    first_run = True

    while True:
        try:
            releases = fetch_feed(feed_url)
            new_count = 0

            for r in releases:
                if r.link in seen:
                    continue
                seen.add(r.link)

                # Skip on first run — just populate seen set to avoid flooding on startup
                if first_run:
                    continue

                if not is_earnings_release(r):
                    continue

                if tickers and not matches_ticker_filter(r, tickers):
                    continue

                print_release(r)
                new_count += 1

            if first_run:
                print(f"Loaded {len(seen)} existing items. Watching for new earnings releases...\n")
                first_run = False
            elif new_count == 0:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] No new earnings releases. Next check in {interval}s...", end="\r")

        except requests.RequestException as e:
            print(f"\n[ERROR] Feed fetch failed: {e}")
        except ET.ParseError as e:
            print(f"\n[ERROR] Feed parse failed: {e}")

        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor PR Newswire for earnings press releases")
    parser.add_argument(
        "--tickers", nargs="+", metavar="TICKER",
        help="Filter by ticker symbol or company name fragment (e.g. META AAPL 'Microsoft')"
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Polling interval in seconds (default: 60, min recommended: 30)"
    )
    parser.add_argument(
        "--feed", choices=list(FEEDS.keys()), default="finance",
        help="Which PR Newswire feed to monitor (default: finance)"
    )
    args = parser.parse_args()

    monitor(
        tickers=args.tickers or [],
        interval=args.interval,
        feed_url=FEEDS[args.feed],
    )


if __name__ == "__main__":
    main()
