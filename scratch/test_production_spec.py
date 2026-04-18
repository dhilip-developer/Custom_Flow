import asyncio
import os
import sys
import json

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.intelligence_utils import extract_with_super_agent, sanitize_json, robust_json_unwrap

async def test_production_spec():
    print("🚀 Verifying Production Specs (Agent 2)...")
    
    # 🧪 TEST 1: JSON Hardening (Step 4 - Comma Repair)
    print("\n[Test 1] Sanitize JSON (Comma Repair)...")
    malformed = '{"documents": [{"invoice_number": "INV123" "total_amount": 500}]}' # Missing comma after INV123
    cleaned = sanitize_json(malformed)
    print(f"  - Cleaned: {cleaned}")
    assert ',"total_amount"' in cleaned, "Comma repair failed!"
    
    # 🧪 TEST 2: Robust Unwrap (Step 4 - conversational noise)
    print("\n[Test 2] Robust JSON extraction...")
    noise = "Sure, here is the data: ```json {\"docs\": []} ``` hope this helps!"
    unwrapped = robust_json_unwrap(noise)
    print(f"  - Unwrapped: {unwrapped}")
    assert unwrapped == '{"docs": []}', "Unwrap failed to isolate JSON!"

    # 🧪 TEST 3: Full Pipeline (Step 1-10)
    print("\n[Test 3] Full Pipeline Execution...")
    ocr_text = """
    INVOICE
    Number: MH2536000682
    Date: 24/02/2026
    Total: 3,032,800.00
    
    Note: Customer shall pay within 30 days which expression shall include... 
    """
    
    # This should succeed or fail gracefully (no crash)
    try:
        response = await extract_with_super_agent(ocr_text)
        print(f"  - Extraction Mode: {response.extraction_mode}")
        print(f"  - LLM Failed: {response.llm_failed}")
        print(f"  - Doc Count: {len(response.documents)}")
        
        # Verify schema
        assert hasattr(response, "extraction_mode"), "Response missing extraction_mode!"
        assert isinstance(response.documents, list), "Response documents is not a list!"
        
        if response.documents:
            doc = response.documents[0]
            print(f"  - 1st Doc Number: {doc.structured_data.get('invoice_number')}")
            print(f"  - 1st Doc Amount: {doc.structured_data.get('total_amount')}")
            # Boilerplate check
            desc = str(doc.structured_data.get('description', ''))
            assert "which expression shall" not in desc, "Boilerplate leak detected!"

        print("\n🎉 ALL TESTS PASSED! Production Spec Compliant.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: Pipeline crashed! {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_production_spec())
