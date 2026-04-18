import requests
import time

def check_agent(name, url):
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            return f"✅ {name:<35} | {url} | Status: OK"
        else:
            return f"❌ {name:<35} | {url} | Status: Code {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ {name:<35} | {url} | Status: FAILED ({str(e)})"

AGENTS = [
    ("Agent 0: Email Scanner", "http://127.0.0.1:30499/docs"),
    ("Agent 1: OCR Extractor", "http://127.0.0.1:30498/docs"),
    ("Agent 2: Classifier", "http://127.0.0.1:30497/docs"),
    ("Agent 3: Data Extractor", "http://127.0.0.1:30496/docs"),
    ("Agent 4: Freight Cert", "http://127.0.0.1:30495/docs"),
    ("Agent 5: Cross Verifier", "http://127.0.0.1:30494/docs"),
    ("Customs Gateway UI", "http://127.0.0.1:30493/ui"),
    ("Insurance Gateway UI", "http://127.0.0.1:30492/"),
    ("Insurance Agent 1: Detector", "http://127.0.0.1:30491/docs"),
    ("Insurance Agent 2: BOL Extractor", "http://127.0.0.1:30490/docs")
]

print("--- CustomsFlow Health Report ---")
for name, url in AGENTS:
    print(check_agent(name, url))
