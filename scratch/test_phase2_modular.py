import asyncio
import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.extraction_engine import extract_structured_data

async def test_modular_flow():
    print("🚀 Starting Phase 2 Modular Refactor Test...")
    
    # Mock OCR text containing mixed content
    sample_ocr = """
    INVOICE
    Invoice No: INV-2026-001
    Date: 25/02/2026
    Buyer: DK CUSTOMS SOLUTIONS
    Total Amount: USD 15,000.50
    GST No: 27AAACB2419H1Z0
    
    -----------------------------------
    
    BILL OF LADING
    B/L Number: MEDU-12345678
    Vessel: OCEAN PRIDE
    Port of Loading: ANTWERP
    Gross Weight: 2,500.00 KG
    
    -----------------------------------
    
    GENERAL CONDITIONS OF SALE
    1. Force Majeure: shall not be liable for any delay...
    2. Limitation of Liability: indemnity shall be restricted...
    3. Jurisdiction: governing law applies...
    """
    
    print("\n--- Processing Sample OCR ---")
    try:
        result = await extract_structured_data(sample_ocr)
        
        print("\n✅ Extraction Results:")
        docs = result.get("documents", [])
        print(f"Total Unique Documents Found: {len(docs)}")
        
        for i, doc in enumerate(docs):
            print(f"\n[Doc {i+1}] Type: {doc['document_type']}")
            data = doc['structured_data']
            for k, v in data.items():
                print(f"  - {k}: {v}")
                
        # Basic assertions
        types = [d['document_type'].lower() for d in docs]
        assert "invoice" in types, "Invoice was missed!"
        assert "bill_of_lading" in types, "BOL was missed!"
        # T&C should be filtered out by merge/garbage filter logic
        assert "terms_and_conditions" not in types, "T&C page was not filtered!"
        
        print("\n🎉 ALL TESTS PASSED! Modular engine is functional.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_modular_flow())
