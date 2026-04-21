import anthropic
import json
import fitz  # PyMuPDF
import requests

# download the earnings report for a specific company and quarter (e.g., AAPL Q4 2023)
url = "https://news.alaskaair.com/company/alaska-air-group-reports-first-quarter-2026-results/"
# "https://s22.q4cdn.com/959853165/files/doc_financials/2026/q1/FINAL-Q1-26-Shareholder-Letter.pdf"
# "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/2025q4-alphabet-earnings-release.pdf"
#"https://s22.q4cdn.com/959853165/files/doc_financials/2025/q4/FINAL-Q4-25-Shareholder-Letter.pdf"
pdf_file = "downloaded_file.pdf"
html_file = "downloaded_file.html"

expectation_file = "expectations.txt"

google_earnings1 = "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q1/2025q1-alphabet-earnings-release.pdf"
google_earnings2 = "https://s206.q4cdn.com/479360582/files/doc_financials/2024/q1/2024q1-alphabet-earnings-release-pdf.pdf"
google_earnings3 = "https://s206.q4cdn.com/479360582/files/doc_financials/2023/q2/2023q2-alphabet-earnings-release.pdf"

gs = "https://www.goldmansachs.com/pressroom/press-releases/current/pdfs/2025-q4-results.pdf"

nflx = "https://s22.q4cdn.com/959853165/files/doc_financials/2026/q1/FINAL-Q1-26-Shareholder-Letter.pdf"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    #"Accept": "application/pdf",
    "Accept": "application/html",
    #"Referer": "https://ir.example.com/"  # replace with actual IR page if known
}

response = requests.get(url, headers=headers)

print(response.status_code)

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
        {"role": "user", "content": f"You are a real-time trading investor, think hard, do you think stock will go up based on these results and expectations? Alaska group (ALK) earnings report: <report> {earnings_report_content} </report> and earnings expectation guidance: <expectation>{expectation_content}</expectation> would you buy ALK stock immediately based on these results and expectations? Respond with simple text yes or no and short summary explaining your reasoning."}
    ]
)
print(message.content[0].text)
# data = json.loads()

#print(data["revenue"])
