import asyncio
import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.extraction_engine.hybrid_engine import extract_with_hybrid_engine

async def verify_blueprint_final():
    print("🚀 Verifying Final Hybrid Blueprint (14 Rules)...")
    
    # 🧪 TEST CASE: Multi-document with noise and numeric comma
    raw_ocr = """
    INVOICE NUMBER: BL-12345
    DATE: 13/04/2026
    TOTAL AMOUNT: 1,500,000.00
    CONSIGNEE: TEST BUYER 1
    
    BILL OF LADING
    BL NUMBER: ONEYSH-9090
    VESSEL: EVER GIVEN 2
    """

    print("\n[Test 1] Executing High-Accuracy Hybrid Extraction...")
    try:
        response = await extract_with_hybrid_engine(raw_ocr)
        
        print(f"  - Extraction Mode: {response.get('extraction_mode')}")
        docs = response.get("documents", [])
        print(f"  - Unique Docs Found: {len(docs)}")
        
        for doc in docs:
            dtype = doc["document_type"]
            sdata = doc["structured_data"]
            print(f"\n📄 Document: {dtype}")
            
            # Verify Normalization (Rule 14)
            if dtype == "invoice":
                amt = sdata.get("total_amount")
                print(f"  🔎 Total Amount: {amt} ({type(amt)})")
                assert isinstance(amt, float), "❌ NORMALIZATION FAILURE: Amount should be float!"
                assert "vessel_name" not in sdata, "❌ PURITY FAILURE: Invoice contains Vessel data!"
                print("  ✅ Normalized & Purified")

            # Verify Strict Mapping (Rule 6/9)
            if dtype == "bill_of_lading":
                assert "invoice_number" not in sdata, "❌ PURITY FAILURE: BL contains Invoice number!"
                print("  ✅ Field Mapping Strictly Enforced")

        print("\n🎉 FINAL HYBRID BLUEPRINT VERIFIED!")
        
    except Exception as e:
        print(f"\n❌ VERIFICATION CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_blueprint_final())
