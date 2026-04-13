import json
import asyncio
from services.intelligence_utils import extract_with_super_agent, merge_extractions
from models.schemas import SuperExtractionResult

def test_pure_merge():
    print("Testing pure merge_extractions logic...")
    docs = [
        SuperExtractionResult(
            document_type="invoice",
            structured_data={"invoice_number": "MH123", "seller_name": "Covestro"}
        ),
        SuperExtractionResult(
            document_type="invoice",
            structured_data={"invoice_number": "MH123", "total_amount": "5000"}
        ),
        SuperExtractionResult(
            document_type="invoice",
            structured_data={"invoice_number": "MH456", "total_amount": "999"}
        )
    ]
    
    merged = merge_extractions(docs)
    print(f"Total merged: {len(merged)}")
    for m in merged:
        print(f"Doc {m.structured_data.get('invoice_number')}: {m.structured_data}")

if __name__ == "__main__":
    test_pure_merge()
