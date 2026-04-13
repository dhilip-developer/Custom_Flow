import json
import asyncio
from services.intelligence_utils import run_customs_intelligence_async

async def test_rule_engine():
    mock_payload = {
        "documents": [
            {
                "document_type": "invoice",
                "structured_data": {
                    "document_number": "INV-123",
                    "total_amount": "5000",
                    "currency": "USD",
                    "bl_number": "BL-001" 
                }
            },
            {
                "document_type": "bill_of_lading",
                "structured_data": {
                    "bl_number": "BL-002", # MISMATCH with Invoice
                    "gross_weight": "500.0",
                    "net_weight": "600.0",  # LOGICAL ERROR: Gross < Net
                    "vessel_name": "Ever Given"
                }
            }
        ]
    }
    
    print("Testing High-Precision Rule-Based Audit Engine...")
    result = await run_customs_intelligence_async(mock_payload)
    
    print("\n[GLOBAL VALIDATION]")
    print(f"Overall Confidence: {result.global_validation.overall_confidence}")
    print(f"Clearance Ready: {result.global_validation.clearance_ready}")
    print(f"Critical Issues: {result.global_validation.critical_issues}")
    print(f"Cross-Doc Issues: {result.global_validation.cross_document_issues}")
    print(f"Warnings: {result.global_validation.warnings}")
    
    print("\n[DOCUMENTS]")
    for doc in result.documents:
        print(f"Type: {doc.document_type}, Score: {doc.confidence_score}")
        if doc.critical_issues: print(f"  - CRITICAL: {doc.critical_issues}")
        if doc.warnings: print(f"  - WARNING: {doc.warnings}")

if __name__ == "__main__":
    asyncio.run(test_rule_engine())
