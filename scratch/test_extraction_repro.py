import requests
import json

url = "http://localhost:30497/extract-super"
data = {
    "total_pages": 33,
    "extracted_pages": 33,
    "raw_text": "Invoice No.: MH2536000682\nDate: 24.02.2026\nBuyer: SEALED AIR PACKAGING MATERIALS (INDIA) LLP\nSeller: Covestro (India) Private Limited\nTotal Amount: 3,032,800.00\nCurrency: INR\n\nHigh Sea Sale Agreement Ref: HSS/COV03031/2025-26\nDate: 24-02-2026\nB/L Number: ONEYSH5ACFU90900\nVessel: OOCL CHARLESTON"
}

try:
    print(f"Sending request to {url}...")
    # The user sent the JSON as text/plain. 
    # Let's try sending it as a string.
    response = requests.post(url, data=json.dumps(data), headers={"Content-Type": "text/plain"}, timeout=120)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
