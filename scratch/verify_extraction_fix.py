import json
import asyncio
from services.intelligence_utils import extract_with_super_agent

async def test_extraction_fix():
    # 1. Test JSON Unwrap
    wrapped_json = '({ "total_pages": 33, "raw_text": "Invoice / Bill of Supply\\nMH2536000682\\nCovestro (India) Private Limited\\nTotal Amount: 3,032,800.00" })'
    print("Testing JSON Unwrap...")
    result_unwrap = await extract_with_super_agent(wrapped_json)
    print(f"Unwrap Result: {len(result_unwrap.documents)} docs found.")
    
    # 2. Test Merging Logic
    print("\nTesting Intelligent Merging Logic...")
    # Mock text with same ID but different data in different parts
    split_text = """
    Invoice / Bill of Supply
    MH2536000682
    Seller: Covestro (India) Private Limited
    
    ... intermediate text ...
    
    Invoice MH2536000682
    Buyer: SEALED AIR PACKAGING MATERIALS (INDIA)LLP
    Total Amount: 3,032,800.00
    """
    
    result_merge = await extract_with_super_agent(split_text)
    print(f"Merge Result: {len(result_merge.documents)} unique docs.")
    
    for i, doc in enumerate(result_merge.documents):
        data = doc.structured_data
        print(f"\nDocument {i+1}: {doc.document_type}")
        print(f"  ID: {data.get('invoice_number')}")
        print(f"  Seller: {data.get('seller_name')}")
        print(f"  Buyer: {data.get('buyer_name')}")
        print(f"  Total: {data.get('total_amount')}")

if __name__ == "__main__":
    asyncio.run(test_extraction_fix())
