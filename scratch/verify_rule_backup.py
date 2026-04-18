import asyncio
import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.intelligence_utils import extract_with_super_agent

async def verify_rule_backup():
    print("🚀 Verifying Rule-Based Fallback & Metadata Cleanup...")
    
    # 🧪 TEST CASE: Text that will trigger LLM failure (since keys are exhausted)
    # the system should catch the 402/429 and trigger Step 8.
    raw_ocr = """
    INVOICE NUMBER: TEST-INV-999
    TOTAL AMOUNT: 500000.00
    """

    print("\n[Test 1] Executing Extraction (Expected LLM Failure)...")
    try:
        response = await extract_with_super_agent(raw_ocr)
        
        print(f"  - Extraction Mode (Top Level): {response.extraction_mode}")
        print(f"  - LLM Failed Flag: {response.llm_failed}")
        print(f"  - Doc Count: {len(response.documents)}")
        
        # Verify and Cleanup
        if response.llm_failed:
            assert response.extraction_mode == "rule_based_fallback", "❌ ERROR: Root mode should be rule_based_fallback!"
            print("  ✅ Root level mode correctly updated to rule_based_fallback.")
        
        # Verify document content (from Regex)
        if response.documents:
            doc = response.documents[0]
            # Check if extraction_engine is MISSING from doc (as per cleanup)
            assert not hasattr(doc, "extraction_engine"), "❌ ERROR: extraction_engine should NOT be in the document!"
            print("  ✅ Document-level engine tag successfully removed.")
            
            data = doc.structured_data
            assert data.get("invoice_number") == "TEST-INV-999", f"❌ ERROR: Regex failed to extract invoice! Found: {data.get('invoice_number')}"
            print("  ✅ Regex Backup successfully extracted critical data.")

        print("\n🎉 RULE-BASED BACKUP & CLEANUP VERIFIED!")
        
    except Exception as e:
        print(f"\n❌ VERIFICATION CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_rule_backup())
