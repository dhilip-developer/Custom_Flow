"""V3 Pipeline Performance Test — verifies batch classification and targeted extraction."""
import asyncio
import os
import time
import glob
from services.document_processor import smart_extract_from_file

# Find the largest PDF in our documents folder for testing
doc_dir = r"c:\Users\dk637\OneDrive\Desktop\Custom-flow\customs_flow_agents(Dhilip)\documents"
pdf_files = glob.glob(os.path.join(doc_dir, "**", "*.pdf"), recursive=True)

if not pdf_files:
    print("ERROR: No PDF files found in documents/ directory")
    exit(1)

# Pick the largest file for the toughest test
pdf_files.sort(key=lambda f: os.path.getsize(f), reverse=True)
test_file = pdf_files[0]
file_size_mb = os.path.getsize(test_file) / (1024 * 1024)

print(f"\n{'='*70}")
print(f"V3 PIPELINE PERFORMANCE TEST")
print(f"File: {os.path.basename(test_file)} ({file_size_mb:.1f} MB)")
print(f"{'='*70}\n")

with open(test_file, "rb") as f:
    file_bytes = f.read()

start = time.time()
try:
    result = asyncio.run(smart_extract_from_file(file_bytes, "application/pdf"))
    duration = time.time() - start

    print(f"\n{'='*70}")
    print(f"  RESULT SUMMARY")
    print(f"{'='*70}")
    print(f"  Total Time:       {duration:.2f}s")
    print(f"  Total Pages:      {result.total_pages}")
    print(f"  Extracted Pages:  {result.extracted_pages}")
    print(f"  Raw Text Length:  {len(result.raw_text)} chars")
    print(f"")
    print(f"  RAW TEXT PREVIEW:")
    print(f"  {result.raw_text[:500]}...")
    print(f"{'='*70}\n")

except Exception as e:
    import traceback
    print(f"\nERROR: {e}")
    traceback.print_exc()
    print(f"{'='*70}\n")
