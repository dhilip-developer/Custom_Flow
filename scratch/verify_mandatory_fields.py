import asyncio
import json
from services.intelligence_utils import extract_chunk_with_gemini
from services.extraction_engine.validation import validate_fields, normalize

async def test_extraction(doc_type, text):
    print(f"\n--- Testing {doc_type} ---")
    results = await extract_chunk_with_gemini(text, doc_type)
    for d in results:
        d = validate_fields(d)
        d = normalize(d)
        print(json.dumps(d, indent=2))

async def main():
    # Invoice Sample
    invoice_text = """
    COMMERCIAL INVOICE
    Invoice No: INV-12345
    Date: 2026-04-18
    Shipper: Global Exports Ltd, 123 Main St, NY
    Consignee: Local Imports LLC, 456 Elm St, Mumbai
    P.O. No: PO-98765
    P.O. Item: 10
    Incoterms: FOB
    Total Amount: 5000.00
    Currency: USD
    GSTIN: 27AAAAA0000A1Z5
    Part No: PN-001
    Description: Widget A
    Country of Origin: USA
    Qty: 100 UNITS
    Unit Price: 50.00
    Net Value: 5000.00
    Gross Value: 5200.00
    HSN Code: 84713010
    """
    await test_extraction("invoice", invoice_text)

    # BOL Sample
    bol_text = """
    BILL OF LADING
    B/L No: BOL-67890
    Date: 2026-04-10
    Shipper: Global Exports Ltd
    Consignee: Local Imports LLC
    Forwarder: Fast Shipping Inc
    Notify Party: Banks & Co
    Vessel: Ocean Queen
    Voyage: V-101
    Port of Loading: New York
    Port of Destination: Mumbai
    Container No: TGBU1234567
    Container Type: 40HQ
    Seal No: S-1234
    Gross Weight: 5000 KGS
    Net Weight: 4800 KGS
    Package Count: 10 PALLETS
    Freight: PREPAID
    Description: 10 Pallets of Electronics
    Measurement: 25.5 CBM
    """
    await test_extraction("bill_of_lading", bol_text)

    # Packing List Sample
    pl_text = """
    PACKING LIST
    Invoice No: INV-12345
    Date: 2026-04-18
    Shipper: Global Exports Ltd
    Consignee: Local Imports LLC
    PO No: PO-98765
    Total Packages: 10
    Gross Weight: 5000 KGS
    Net Weight: 4800 KGS
    Marks & Numbers: MARK-001/010
    Qty: 100
    Pallet Details: 10 Wooden Pallets
    Part Number: PN-001
    Country of Origin: USA
    HS Code: 84713010
    Description: Widget A
    """
    await test_extraction("packing_list", pl_text)

if __name__ == "__main__":
    asyncio.run(main())
