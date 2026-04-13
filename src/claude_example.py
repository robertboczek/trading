import anthropic
import json
import fitz  # PyMuPDF
import requests

# download the earnings report for a specific company and quarter (e.g., AAPL Q4 2023)
url = "https://s22.q4cdn.com/959853165/files/doc_financials/2025/q4/FINAL-Q4-25-Shareholder-Letter.pdf"
pdf_file = "downloaded_file.pdf"

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
        {"role": "user", "content": f"Can you extract Q4 revenue from earnings report: <report>{earnings_report_content}</report>? Respond with json format: {{\"revenue\": \"value\"}} and nothing else."}
    ]
)
print(message.content[0].text)
# data = json.loads()

#print(data["revenue"])
