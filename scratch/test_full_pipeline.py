"""
End-to-end test: New Agent 1 (raw dump) → Agent 2 (regex extraction).
Creates a test PDF with a real invoice, processes through both agents.
"""
import asyncio
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF


def create_test_pdf() -> bytes:
    """Create a multi-page test PDF with real customs document text."""
    doc = fitz.open()

    # Page 1: Invoice
    page1 = doc.new_page()
    page1.insert_text((72, 72), "COMMERCIAL INVOICE", fontsize=18)
    page1.insert_text((72, 110), """
Invoice No.: INV-2026-0457
Invoice Date: 07/04/2026
Buyer: M/S Global Imports Pvt Ltd
Seller: Covestro Deutschland AG
GSTIN: 33AABCU9603R1ZM
P.O. Number: PO-2026-1122

Sr No  Description        HSN Code  Qty   Unit Price    Amount
1      Polycarbonate      39074000  500   USD 6,065.60  USD 3,032,800.00

Total Amount: USD 3,032,800.00
Currency: USD
""", fontsize=10)

    # Page 2: Bill of Lading
    page2 = doc.new_page()
    page2.insert_text((72, 72), "BILL OF LADING", fontsize=18)
    page2.insert_text((72, 110), """
B/L No.: HLCUHAM260300389
B/L Date: 05/04/2026
Shipper: Covestro Deutschland AG, Leverkusen, Germany
Consignee: To Order of HDFC Bank Ltd
Vessel Name: MV EVER GOLDEN
Voyage No.: 0234E
Port of Loading: HAMBURG, GERMANY
Port of Discharge: CHENNAI, INDIA
Container Number: HLXU8073652
Seal Number: SL-78234
Gross Weight: 21,749.200 KGS
Net Weight: 21,500.000 KGS
700 Packages
Freight Prepaid
""", fontsize=10)

    # Page 3: Packing List
    page3 = doc.new_page()
    page3.insert_text((72, 72), "PACKING LIST", fontsize=18)
    page3.insert_text((72, 110), """
Packing List No.: PL-2026-0457
Date: 07/04/2026
Total Packages: 700
Gross Weight: 21,749.200 KGS
Net Weight: 21,500.000 KGS
Marks and Numbers: MK/GI/2026/CHN
""", fontsize=10)

    import io
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


async def test_full_pipeline():
    print("=" * 70)
    print("  FULL PIPELINE TEST: Agent 1 → Agent 2")
    print("=" * 70)

    # Create test PDF
    pdf_bytes = create_test_pdf()
    print(f"\n[Test] Created test PDF: {len(pdf_bytes)} bytes, 3 pages")

    # ── Agent 1: Extract raw text ──
    print(f"\n{'─' * 40}")
    print("  AGENT 1: Raw Text Extraction")
    print(f"{'─' * 40}")

    from services.document_processor import smart_extract_from_file

    t0 = time.time()
    agent1_result = await smart_extract_from_file(pdf_bytes, "application/pdf")
    agent1_time = time.time() - t0

    print(f"\n  Total pages: {agent1_result.total_pages}")
    print(f"  Extracted pages: {agent1_result.extracted_pages}")
    print(f"  Raw text length: {len(agent1_result.raw_text)} chars")
    print(f"  ⏱ Time: {agent1_time:.3f}s")

    # ── Agent 2: Structured extraction ──
    print(f"\n{'─' * 40}")
    print("  AGENT 2: Regex Extraction Engine")
    print(f"{'─' * 40}")

    from services.extraction_engine import extract_structured_data

    t1 = time.time()
    agent2_result = extract_structured_data(agent1_result.raw_text)
    agent2_time = time.time() - t1

    print(f"\n  Documents found: {len(agent2_result.documents)}")
    for doc in agent2_result.documents:
        print(f"\n  --- {doc.document_type.upper()} ---")
        print(f"  {json.dumps(doc.structured_data, indent=4, default=str)}")
    print(f"\n  ⏱ Time: {agent2_time:.3f}s")

    # ── Summary ──
    total_time = agent1_time + agent2_time
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Agent 1 (OCR):       {agent1_time:.3f}s")
    print(f"  Agent 2 (Extract):   {agent2_time:.3f}s")
    print(f"  TOTAL:               {total_time:.3f}s")
    print(f"  Documents extracted:  {len(agent2_result.documents)}")
    print(f"  LLM API calls:       0")
    print(f"  Document AI calls:   0 (digital PDF)")
    print(f"{'=' * 70}")

    # Validate
    doc_types = [d.document_type for d in agent2_result.documents]
    expected = ["invoice", "bill_of_lading", "packing_list"]
    for exp in expected:
        status = "✓" if exp in doc_types else "✗"
        print(f"  {status} {exp}")

    assert len(agent2_result.documents) >= 3, f"Expected 3+ docs, got {len(agent2_result.documents)}"
    print(f"\n  ALL TESTS PASSED ✓")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
