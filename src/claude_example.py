import time

import anthropic
import json
import fitz  # PyMuPDF
import requests

# download the earnings report for a specific company and quarter (e.g., AAPL Q4 2023)
url = "https://www.intc.com/news-events/press-releases/detail/1767/intel-reports-first-quarter-financial-results"
# "https://www.intc.com/news-events/press-releases/detail/1767/intel-reports-first-quarter-2026-financial-results"
# "https://assets-ir.tesla.com/tesla-contents/IR/TSLA-Q1-2026-Update.pdf"
# "https://news.alaskaair.com/company/alaska-air-group-reports-first-quarter-2026-results/"
# "https://s22.q4cdn.com/959853165/files/doc_financials/2026/q1/FINAL-Q1-26-Shareholder-Letter.pdf"
# "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/2025q4-alphabet-earnings-release.pdf"
#"https://s22.q4cdn.com/959853165/files/doc_financials/2025/q4/FINAL-Q4-25-Shareholder-Letter.pdf"
pdf_file = "downloaded_file.pdf"
html_file = "downloaded_file.html"

expectation_file = "expectations-tsla.txt"

google_earnings1 = "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q1/2025q1-alphabet-earnings-release.pdf"
google_earnings2 = "https://s206.q4cdn.com/479360582/files/doc_financials/2024/q1/2024q1-alphabet-earnings-release-pdf.pdf"
google_earnings3 = "https://s206.q4cdn.com/479360582/files/doc_financials/2023/q2/2023q2-alphabet-earnings-release.pdf"

gs = "https://www.goldmansachs.com/pressroom/press-releases/current/pdfs/2025-q4-results.pdf"

nflx = "https://s22.q4cdn.com/959853165/files/doc_financials/2026/q1/FINAL-Q1-26-Shareholder-Letter.pdf"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    #"Accept": "application/pdf",
    "Accept": "application/html",
    "Referer": "https://ir.example.com/"  # replace with actual IR page if known
}

response = requests.get(url, headers=headers)

print(response.status_code)

#time.sleep(100)

# Check if the request was successful
if response.status_code == 200:
    with open(html_file, "wb") as f:
        f.write(response.content)

doc = fitz.open(html_file)
earnings_report_content = ""
for page in doc:
    earnings_report_content += page.get_text()

doc = fitz.open(expectation_file)
expectation_content = ""
for page in doc:
    expectation_content += page.get_text()

# print(earnings_report_content)
# print(expectation_content)



# The SDK automatically looks for the ANTHROPIC_API_KEY environment variable
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-opus-4-7", # Select your model (e.g., Sonnet or Opus)
    max_tokens=6000,
    messages=[
        #{"role": "user", "content": f"Can you extract Q4 revenue from earnings report: <report>{earnings_report_content}</report>? Respond with json format: {{\"revenue\": \"value\"}} and nothing else."}
        #{"role": "user", "content": f"Given these Q4 earnings results from earnings report: <report>{earnings_report_content}</report> given expected EPS was $2.57-$2.64 and expected Q4 revenue was $111.43B. Apart from raw revenue and EPS analyze capex compared to previous periods and whether it's positive or negative for the stock? Think as a real-time trading investor, would you buy this stock immediately based on these results? Respond with simple text yes or no where yes indicates investors to react positively and no otherwise."}
        #{"role": "user", "content": f"You are a real-time trading investor, think hard, do you think stock will go up based on these results and expectations? TSLA earnings report: <report> {earnings_report_content} </report> and earnings expectation guidance: <expectation>{expectation_content}</expectation> would you buy TSLA stock immediately based on these results and expectations? Respond with simple text yes or no and short summary explaining your reasoning."}
        {"role": "user", "content": f"You are a real-time trading investor, think hard, are you bearish, neutral or bullish on INTL stock based on these results and expectations? INTL earnings report: <report> {earnings_report_content} </report> and earnings expectation guidance: <expectation>{expectation_content}</expectation>. Respond with simple text bearish, neutral or bullish and short summary explaining your reasoning."}
    ]
)
print(message.content[0].text)
# data = json.loads()

#print(data["revenue"])
