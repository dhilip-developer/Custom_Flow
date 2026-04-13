import asyncio
import os
import time
import glob
import sys

# Set up paths
sys.path.append(os.getcwd())

from services.document_processor import smart_extract_from_file
from services.intelligence_utils import extract_with_super_agent
import json

async def live_run():
    print("\n" + "="*70)
    print("🚀 CUSTOMS FLOW: LIVE PROCESSING RUN (V1.0 FINAL)")
    print("="*70)

    # 1. Locate the test file
    doc_dir = r"c:\Users\dk637\OneDrive\Desktop\Custom-flow\customs_flow_agents(Dhilip)\documents"
    pdf_files = glob.glob(os.path.join(doc_dir, "**", "*.pdf"), recursive=True)
    if not pdf_files:
        print("❌ ERROR: No PDF files found")
        return
        
    pdf_files.sort(key=lambda f: os.path.getsize(f), reverse=True)
    test_file = pdf_files[0]
    print(f"📄 Targeting: {os.path.basename(test_file)} ({os.path.getsize(test_file)/1024/1024:.2f} MB)")

    # 2. Stage A: OCR & Document Reconstruction (Agent 1)
    print("\n[Stage A] Running Agent 1 (Smart OCR)...")
    with open(test_file, "rb") as f:
        file_bytes = f.read()
    
    t0 = time.time()
    ocr_result = await smart_extract_from_file(file_bytes, "application/pdf")
    print(f"✅ OCR Complete: {ocr_result.extracted_pages} pages in {time.time()-t0:.2f}s")

    # 3. Stage B: Hardened Structured Extraction (Agent 2)
    print("\n[Stage B] running Agent 2 (Advanced Intelligence Engine)...")
    print("[Protocol] Flowchart-Aligned / Normalization Active")
    
    t1 = time.time()
    intelligence_result = await extract_with_super_agent(ocr_result.raw_text)
    print(f"✅ Intelligence Complete: Found {len(intelligence_result.documents)} logical documents in {time.time()-t1:.2f}s")

    # 4. Display Results
    print("\n" + "="*70)
    print(" FINAL STRUCTURED EXTRACTION OUTPUT")
    print("="*70)
    
    for i, doc in enumerate(intelligence_result.documents, 1):
        print(f"\n--- Document #{i}: {doc.document_type.upper()} ---")
        # Pretty print the structured data
        print(json.dumps(doc.structured_data, indent=2))
        print("-" * 40)

    total_time = time.time() - t0
    print(f"\n✨ LIVE RUN COMPLETE in {total_time:.2f}s")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(live_run())
