import asyncio
from services.intelligence_utils import verify_extracted_data_async

async def main():
    print("Testing Invoice (Partial)...")
    invoice_data = {
        "invoice_number": "INV-100",
        "total_amount": 5000,
        "currency": "USD"
        # Missing seller_name, buyer_name, invoice_date
    }
    res = await verify_extracted_data_async("Invoice", invoice_data)
    print(f"Status: {res.status}")
    print(f"Confidence: {res.confidence}")
    print(f"Details: {res.details}")
    print(f"Missing Fields: {res.missing_fields}")
    print("-" * 40)

    print("Testing BOL (Verified)...")
    bol_data = {
        "bl_number": "BOL-999",
        "bl_date": "2024-01-01",
        "shipper": "Shipper A",
        "consignee": "Consignee B",
        "vessel_name": "Ocean Star",
        "port_of_loading": "NY",
        "port_of_destination": "London",
        "container_number": "CONT-123",
        "gross_weight": "1000",
        "net_weight": "900"
    }
    res = await verify_extracted_data_async("Bill of Lading", bol_data)
    print(f"Status: {res.status}")
    print(f"Confidence: {res.confidence}")
    print(f"Details: {res.details}")
    print(f"Missing Fields: {res.missing_fields}")
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
