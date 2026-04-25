import os
import sys

from datetime import datetime
import time
from xmlrpc import client

import anthropic

import anthropic


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value

def sleep_until(target_time):
    now = datetime.now()
    delta = (target_time - now).total_seconds()
    
    if delta > 0:
        time.sleep(delta)

def print_time():
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

def get_headers(accept_type):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        #"Accept": "application/pdf", application/html
        "Accept-Language": "en-US,en;q=0.5",
        "Accept": accept_type,
        "Referer": "https://ir.example.com/"  # replace with actual IR page if known
    }

def query_claude(ticker, expectation_content, earnings_report_content):
    # The SDK automatically looks for the ANTHROPIC_API_KEY environment variable
    client = anthropic.Anthropic()

    client.messages.create(
        model="claude-opus-4-7", # Select your model (e.g., Sonnet or Opus)
        max_tokens=6000,
        messages=[
            #{"role": "user", "content": f"Can you extract Q4 revenue from earnings report: <report>{earnings_report_content}</report>? Respond with json format: {{\"revenue\": \"value\"}} and nothing else."}
            #{"role": "user", "content": f"Given these Q4 earnings results from earnings report: <report>{earnings_report_content}</report> given expected EPS was $2.57-$2.64 and expected Q4 revenue was $111.43B. Apart from raw revenue and EPS analyze capex compared to previous periods and whether it's positive or negative for the stock? Think as a real-time trading investor, would you buy this stock immediately based on these results? Respond with simple text yes or no where yes indicates investors to react positively and no otherwise."}
            #{"role": "user", "content": f"You are a real-time trading investor, think hard, do you think stock will go up based on these results and expectations? TSLA earnings report: <report> {earnings_report_content} </report> and earnings expectation guidance: <expectation>{expectation_content}</expectation> would you buy TSLA stock immediately based on these results and expectations? Respond with simple text yes or no and short summary explaining your reasoning."}
            {"role": "user", "content": f"You are a real-time trading investor, think hard, are you bearish, neutral or bullish on {ticker} stock based on these results and expectations? {ticker} earnings report: <report> {earnings_report_content} </report> and earnings expectation guidance: <expectation>{expectation_content}</expectation>. Respond with simple text bearish, neutral or bullish and short summary explaining your reasoning."}
        ]
    )