import socket
import sys

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except:
            return False

AGENTS = [
    ("Agent 0: Email Scanner", 30499),
    ("Agent 1: OCR Extractor", 30498),
    ("Agent 2: Classifier", 30497),
    ("Agent 3: Data Extractor", 30496),
    ("Agent 4: Freight Cert", 30495),
    ("Agent 5: Cross Verifier", 30494),
    ("Customs Gateway UI", 30493),
    ("Insurance Gateway UI", 30492),
    ("Insurance Agent 1: Detector", 30491),
    ("Insurance Agent 2: BOL Extractor", 30490)
]

print("--- CustomsFlow Agent Status Check ---")
all_running = True
for name, port in AGENTS:
    status = "RUNNING" if check_port(port) else "FAILED"
    if status == "FAILED":
        all_running = False
    print(f"{name:<35} | Port: {port} | Status: {status}")

if all_running:
    print("\n[SUCCESS] All 10 microservices are reachable.")
    sys.exit(0)
else:
    print("\n[ERROR] Some microservices are not reachable. Please check run.py logs.")
    sys.exit(1)
