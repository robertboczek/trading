import anthropic
import json
import fitz  # PyMuPDF
import requests

# download the earnings report for a specific company and quarter (e.g., AAPL Q4 2023)
url = "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/2025q4-alphabet-earnings-release.pdf"
#"https://s22.q4cdn.com/959853165/files/doc_financials/2025/q4/FINAL-Q4-25-Shareholder-Letter.pdf"
pdf_file = "downloaded_file.pdf"

google_earnings1 = "https://s206.q4cdn.com/479360582/files/doc_financials/2025/q1/2025q1-alphabet-earnings-release.pdf"
google_earnings2 = "https://s206.q4cdn.com/479360582/files/doc_financials/2024/q1/2024q1-alphabet-earnings-release-pdf.pdf"
google_earnings3 = "https://s206.q4cdn.com/479360582/files/doc_financials/2023/q2/2023q2-alphabet-earnings-release.pdf"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/pdf",
    #"Referer": "https://ir.example.com/"  # replace with actual IR page if known
}

response = requests.get(url, headers=headers)

print(response.status_code)

# Check if the request was successful
if response.status_code == 200:
    with open(pdf_file, "wb") as f:
        f.write(response.content)

doc = fitz.open(pdf_file)
earnings_report_content = ""
for page in doc:
    earnings_report_content += page.get_text()

# print(earnings_report_content)

# The SDK automatically looks for the ANTHROPIC_API_KEY environment variable
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-opus-4-6", # Select your model (e.g., Sonnet or Opus)
    max_tokens=1024,
    messages=[
        #{"role": "user", "content": f"Can you extract Q4 revenue from earnings report: <report>{earnings_report_content}</report>? Respond with json format: {{\"revenue\": \"value\"}} and nothing else."}
        {"role": "user", "content": f"Given these Q4 earnings results from earnings report: <report>{earnings_report_content}</report> given expected EPS was $2.57-$2.64 and expected Q4 revenue was $111.43B. Apart from raw revenue and EPS analyze capex compared to previous periods and whether it's positive or negative for the stock? Think as a real-time trading investor, would you buy this stock immediately based on these results? Respond with simple text yes or no where yes indicates investors to react positively and no otherwise."}
    ]
)
print(message.content[0].text)
# data = json.loads()

#print(data["revenue"])
