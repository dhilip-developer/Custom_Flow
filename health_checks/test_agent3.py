import asyncio
from services.intelligence_utils import extract_data_from_text

def test_agent_3():
    # Test 1: Known Document Type (snake_case from V3 pipeline)
    print("--- Test 1: invoice ---")
    res1 = extract_data_from_text("invoice", "Billed To: Custom Flow Logistics\n123 Street Ave, Dubai, UAE\nInvoice Date: 2024-03-01\nTotal Value: $5,000 USD\nHS Code: 8542.31\nMaterial: Microchips")
    print(res1)
    
    # Test 2: Fallback Document Type (generic_customs_document)
    print("\n--- Test 2: generic_customs_document ---")
    res2 = extract_data_from_text("generic_customs_document", "Certificate of Final Inspection\nDate: 2024-02-15\nInspector: John Doe\nResult: PASS\nRemarks: All boxes properly sealed.")
    print(res2)

if __name__ == "__main__":
    test_agent_3()
