"""
Centralised configuration for all CustomsFlow agents.
Handles .env loading, Google credentials, port assignments, and CORS setup.
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Resolve project root (one level up from shared/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure project root is on sys.path so imports like `services.*`, `models.*` work
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Load .env and Google credentials
# ---------------------------------------------------------------------------

import json

# Global configuration objects populated by load_credentials()
DOCAI_CONFIG = {
    "project_id": None,
    "location": "us",
    "processor_id": None,
    "credentials_file": "google-credentials.json"
}

EMAIL_ACCOUNTS = {
    "Gmail": {
        "email": "boostentryai@gmail.com",
        "password": None, # App password
        "imap_server": "imap.gmail.com",
        "folders": ["INBOX", "[Gmail]/All Mail", "[Gmail]/Spam"]
    },
    "Zoho": {
        "email": "ctalert@workboosterai.com",
        "password": None, # App password
        "imap_server": "imap.zoho.in",
        "folders": ["INBOX", "Spam", "Junk"]
    }
}

def load_credentials():
    """Load credentials from a visible secrets.json file to avoid FTP .env drops."""
    secrets_path = os.path.join(PROJECT_ROOT, "secrets.json")
    
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
            
            # Inject all string values from secrets.json into the OS environment
            for key, value in secrets.items():
                if isinstance(value, str):
                    os.environ[key] = value
                
            # If a service account is declared, set it and override the standard key
            if "GOOGLE_APPLICATION_CREDENTIALS" in secrets:
                if "GEMINI_API_KEY" in os.environ:
                    del os.environ["GEMINI_API_KEY"]
            
            # Update Document AI Config from secrets
            DOCAI_CONFIG["location"] = secrets.get("DOCAI_LOCATION", "us")
            DOCAI_CONFIG["processor_id"] = secrets.get("DOCAI_PROCESSOR_ID")
            DOCAI_CONFIG["credentials_file"] = secrets.get("DOCAI_CREDENTIALS_FILE", "google-credentials.json")
            
            # Auto-detect Project ID from the credentials file if possible
            cred_file = os.path.join(PROJECT_ROOT, DOCAI_CONFIG["credentials_file"])
            if os.path.exists(cred_file):
                try:
                    with open(cred_file, "r") as cf:
                        cred_data = json.load(cf)
                        DOCAI_CONFIG["project_id"] = cred_data.get("project_id")
                except:
                    pass

            # Update Email Config from secrets
            EMAIL_ACCOUNTS["Gmail"]["password"] = secrets.get("GMAIL_APP_PASSWORD")
            EMAIL_ACCOUNTS["Zoho"]["password"] = secrets.get("ZOHO_APP_PASSWORD")

            # Warning if missing
            if not EMAIL_ACCOUNTS["Gmail"]["password"]:
                print("WARNING: GMAIL_APP_PASSWORD not found in secrets.json or Environment.")
            if not EMAIL_ACCOUNTS["Zoho"]["password"]:
                print("WARNING: ZOHO_APP_PASSWORD not found in secrets.json or Environment.")

        except json.JSONDecodeError:
            print(f"ERROR: Configuration file {secrets_path} contains invalid JSON.")
    else:
        print(f"WARNING: Configuration file not found at {secrets_path}")


# ---------------------------------------------------------------------------
# Port assignments (Agent 0 → 30499 descending)
# ---------------------------------------------------------------------------

AGENT_PORTS = {
    "agent0_email_scanner": 30499,
    "agent1_ocr_extractor": 30498,
    "agent2_data_extractor": 30497,
    "agent3_classifier": 30496,
    "agent4_freight_cert": 30495,
    "agent5_cross_verifier": 30494,
    "gateway": 30493,
}


# ---------------------------------------------------------------------------
# CORS helper — apply permissive CORS to any FastAPI app
# ---------------------------------------------------------------------------

def add_cors(app: FastAPI):
    """Attach permissive CORS middleware to a FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
