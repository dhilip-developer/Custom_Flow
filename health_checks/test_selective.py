"""Verification script for Fast Selective Extraction."""
from shared.config import load_credentials
load_credentials()

from services.document_processor import smart_extract_from_file
import os
import time

pdf_dir = r"c:\Users\dk637\OneDrive\Desktop\Custom-flow\customs_flow_agents(Dhilip)\documents\hibhaworkbooster_at_gmail.com_Wed,_8_Apr_2026_14_10_57__0530"

# Target file to test speed increase
fname = "DACHSER_Bill_Of_Lading_-_69500389580.pdf" 
fpath = os.path.join(pdf_dir, fname)

print(f"\n{'='*70}")
print(f"TESTING FAST SELECTIVE EXTRACTION: {fname}")
print(f"{'='*70}")

with open(fpath, "rb") as f:
    file_bytes = f.read()

start_time = time.time()
try:
    result = smart_extract_from_file(file_bytes, "application/pdf")
    duration = time.time() - start_time
    
    print(f"\n  COMPLETED in {duration:.2f}s")
    print(f"  Total Pages: {result.total_pages}")
    print(f"  Extracted Pages: {result.extracted_pages}")
    print(f"  Raw Text Size: {len(result.raw_text)} chars")

except Exception as e:
    print(f"ERROR: {e}")

print(f"\n{'='*70}")
