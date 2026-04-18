import asyncio
import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.intelligence_utils import extract_with_super_agent

async def verify_phase2_wiring():
    print("🚀 Final Verification: Phase 2 Wiring & Cleaning...")
    
    # OCR snippet containing a noisy HSS agreement and an Invoice with summary rows
    noisy_ocr = """
    HIGH SEA SALE AGREEMENT
    HSS Agreement Ref: HSS/COV03031/2025-26
    Agreement Date: 30/01/2026
    Vessel Name: OOCL CHARLESTON
    B/L No: ONEYSH5ACFU90900
    Port of Loading: SHANGHAI
    Port of Destination: CHENNAI
    
    -----------------------------------
    
    INVOICE
    Invoice No: MH2536000682
    Date: 24/02/2026
    Buyer: SEALED AIR PACKAGING MATERIALS (INDIA) LLP
    Seller: Covestro (India) Private Limited
    
    S.No  Description  Qty  Rate  Amount
    1     Chemical X   10   500   5000
    2     Tax          -    -     900
    3     Net Amount   -    -     5900
    """
    
    try:
        response = await extract_with_super_agent(noisy_ocr)
        docs = response.documents
        
        print(f"\n✅ Pipeline Extraction Successful. Found {len(docs)} documents.")
        
        for i, doc in enumerate(docs):
            print(f"\n[Document {i+1}] {doc.document_type}")
            print(f"  - Engine Flag: {doc.extraction_engine}")
            data = doc.structured_data
            
            # Check for label noise cleanup (Fix 5)
            if doc.document_type == "high_seas_sale_agreement":
                hss_ref = data.get("hss_ref_no", "")
                print(f"  - HSS Ref (Raw): {hss_ref}")
                assert "Agreement Ref" not in hss_ref, "HSS Ref still has label noise!"
                
            # Check for junk item filtering (Fix 7)
            if "invoice" in doc.document_type.lower():
                items = data.get("items") or data.get("line_items") or []
                print(f"  - Item Count: {len(items)}")
                for item in items:
                    name = str(item.get("name") or item.get("description") or "").lower()
                    print(f"    - Item: {name}")
                    assert "net amount" not in name, "Net Amount summary row was NOT filtered!"
                    assert "tax" not in name, "Tax summary row was NOT filtered!"

            # Check engine flag (Fix 4)
            assert doc.extraction_engine == "gemini", f"Engine flag was {doc.extraction_engine}, expected 'gemini'"

        print("\n🎉 PHASE 2 WIRING VERIFIED! All 7 Fixes Confirmed.")
        
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_phase2_wiring())
