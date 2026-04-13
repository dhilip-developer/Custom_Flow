import json
import asyncio
from services.intelligence_utils import extract_with_super_agent

async def test_gemini_pipeline():
    # Construct a noisy, multi-document string
    mock_text = """
    Invoice No: INV-001
    Buyer: Acme Corp
    Seller: Global Trade
    Total: 1500 USD
    Items: 2x Widgets
    
    This is some noisy text in the middle...
    
    Bill of Lading
    BL No: BL-999
    Vessel: Ever Given
    Port: Jebel Ali
    Weight: 5000 kg
    
    Invoice No: INV-001
    Buyer: Acme Corp
    Seller: Global Trade
    Total: 1500 USD
    """
    
    print("Testing Gemini Flash Chunking Pipeline...")
    # This will call the real Gemini API using the new key
    result = await extract_with_super_agent(mock_text)
    
    print("\n[EXTRACTION SUMMARY]")
    print(f"Total Documents Found: {len(result.documents)}")
    
    for i, doc in enumerate(result.documents):
        print(f"\nDocument {i+1}: {doc.document_type}")
        print(json.dumps(doc.structured_data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_gemini_pipeline())
