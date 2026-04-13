import subprocess
import time
import sys
import os

AGENTS = [
    ("Agent 0: Email Scanner", "agent0_email_scanner/main.py", 30499),
    ("Agent 1: OCR Extractor", "agent1_ocr_extractor/main.py", 30498),
    ("Agent 2: Data Extractor", "agent2_data_extractor/main.py", 30497),
    ("Agent 3: Classifier", "agent3_classifier/main.py", 30496),
    ("Agent 4: Freight Cert", "agent4_freight_cert/main.py", 30495),
    ("Agent 5: Cross Verifier", "agent5_cross_verifier/main.py", 30494),
    ("Customs Gateway UI", "gateway_ui/main.py", 30493),
    ("Insurance Gateway UI", "insurance_gateway_ui/main.py", 30492),
    ("Insurance Agent 1: Detector", "insurance_agent1_detector/main.py", 30491),
    ("Insurance Agent 2: BOL Extr.", "insurance_agent2_bol/main.py", 30490)
]

processes = []

def start_agents():
    # Setup environment for cleaner logs
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    print("\n" + "="*60)
    print(" CUSTOMS FLOW: STARTING 10-AGENT MICROSERVICES ENVIRONMENT")
    print("="*60 + "\n")
    
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    for name, path, port in AGENTS:
        try:
            # We suppress STDOUT and only allow Errors to flow through
            # This keeps the terminal clean while still showing crashes
            p = subprocess.Popen(
                [sys.executable, path],
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL, # Suppress normal logs
                stderr=None               # Allow errors to show
            )
            processes.append((name, p))
            time.sleep(0.5) 
        except Exception as e:
            print(f"  [!] CRITICAL ERROR starting {name}: {e}")

    print("--- ACCESS LINKS ---")
    print(f"👉 CUSTOMS DASHBOARD:   http://localhost:30493/")
    print(f"👉 INSURANCE DASHBOARD: http://localhost:30492/")
    print("-" * 60)
    print("Individual Agent Docs (FastAPI):")
    for name, _, port in AGENTS:
        print(f"  → {name:<25}: http://localhost:{port}/docs")
    print("-" * 60)
    print("All services are running. Logs are suppressed. Errors will appear below if they occur.")
    print("Press Ctrl+C to stop all agents.\n")

    try:
        # Keep the script alive while sub-processes are running
        while True:
            time.sleep(1)
            # Optional: Check if any process has exited prematurely
            for name, p in processes:
                if p.poll() is not None:
                    print(f"  [!] WARNING: {name} has stopped (PID: {p.pid})")
                    processes.remove((name, p))
    except KeyboardInterrupt:
        print("\nGracefully stopping all microservices...")
        for name, p in processes:
            p.terminate()
            p.wait()
            print(f"  [√] Stopped {name.strip()}.")

if __name__ == "__main__":
    start_agents()
