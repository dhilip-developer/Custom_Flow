import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.extraction_engine.segmentation import segment_documents

# Simulated 33-page style text with mixed documents
MOCK_TEXT = """
INV/2026/001
TAX INVOICE
Seller: SEALED AIR PACKAGING
Buyer: 20 CUBE WHSING
Date: 30-01-2026
Invoice No: C831
Product: INSTAPAK CHEMICAL A - 20000 KG - 150.00
Product: INSTAPAK CHEMICAL B - 10000 KG - 120.00
Total: 3032800
... (imagine 10 pages of terms) ...
""" + ("\nTERMS AND CONDITIONS LINE " * 500) + """
HIGH SEAS SALE AGREEMENT
This agreement is made on 24-02-2026
Between: Covestro (India) Private Limited (Seller)
And: 20 Cube Warehousing (Buyer)
Goods: CHEMICALS
Value: 5000000
... (imagine 10 pages of agreement) ...
""" + ("\nAGREEMENT CLAUSE " * 500) + """
SEA WAYBILL
B/L No: SB123456
Port of Loading: MUMBAI
Port of Discharge: DUBAI
Vessel: EVER GREEN
Gross Weight: 30000 KG
"""

async def test_flow():
    print("--- TESTING SEGMENTATION ---")
    segments = segment_documents(MOCK_TEXT)
    print(f"Total Segments Found: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"Segment {i+1}: Type={seg['document_type']}, Length={len(seg['text'])}")

    from services.extraction_engine.hybrid_engine import extract_with_hybrid_engine
    import json
    
    print("\n--- TESTING HYBRID EXTRACTION ---")
    result = await extract_with_hybrid_engine(MOCK_TEXT)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_flow())
