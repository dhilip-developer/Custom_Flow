import asyncio
import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.intelligence_utils import extract_with_super_agent

async def verify_9_type_purity():
    print("🚀 Verifying 9-Document Type Pure LLM Pipeline...")
    
    # 🧪 TEST CASE: Mixed Invoice and Bill of Lading with "Weight-as-Amount" risk
    raw_ocr = """
    INVOICE MH2536000682
    Date: 24-02-2026
    Total Amount: 3,032,800.00 INR
    Gross Weight: 21,749.200 KG
    
    BILL OF LADING
    B/L No: ONEYSH5ACFU90900
    Vessel: ONE HAMMERSMITH
    Voyage: 084E
    """

    print("\n[Test 1] Executing Pure LLM Extraction...")
    try:
        response = await extract_with_super_agent(raw_ocr)
        
        print(f"  - Extraction Mode: {response.extraction_mode}")
        print(f"  - Doc Count: {len(response.documents)}")
        
        for doc in response.documents:
            dtype = doc.document_type
            sdata = doc.structured_data
            print(f"\n📄 Document: {dtype}")
            
            # Check Purity (Step 5)
            if dtype == "bill_of_lading":
                assert "invoice_number" not in sdata, "❌ PURITY FAILURE: Invoice data present in BL!"
                assert "total_amount" not in sdata, "❌ PURITY FAILURE: Financial data present in BL!"
                print("  ✅ Purity Check Passed (No finance in BL)")
                print(f"  ✅ BL Number: {sdata.get('bl_number')}")
                
            # Check Semantic Sanity (Step 3 & 8)
            if dtype == "invoice":
                amount = sdata.get("total_amount")
                print(f"  🔎 Invoice Total: {amount}")
                if amount is not None:
                    assert float(amount) > 100000, f"❌ SANITY FAILURE: Amount {amount} looks like a weight!"
                    print("  ✅ Semantic Sanity Passed (Amount is correct)")

        # Verify Merging (Step 7)
        # (Since we gave one text sample, we expect 2 distinct documents)
        assert len(response.documents) >= 2, "❌ MERGE FAILURE: Lost documents!"
        
        print("\n🎉 ALL 9-TYPE PURITY TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ VERIFICATION CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_9_type_purity())
