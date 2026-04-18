import asyncio
import json
import sys
import os

# Add parent dir to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction_engine.hybrid_engine import extract_with_hybrid_engine

RAW_TEXT_SAMPLE = """
101095556
B210 CB 165X300 STD
3923210000
CN      20.600      MU
USD 48.78883        USD    1,005.05
SEUT B NA7AQ
SAQA3264 B82-1KG Pizza Cheese Moz165x300
SEALED AIR (CHINA) CO., LTD.
6988 SONGZE AVENUE
QINGPU INDUSTRIAL PARK SHANGHAI 201705
China
Tel: 86-21-3920-2988
Fax: 86-21-3920-2980
Note: Tax1 = VAT
Total net value                  USD      1,005.05
Total Freight
USD          0.00
Total Tax1
Total Tax
Downpayment
USD          0.00
TOTAL
USD      1,005.05
INVOICE
Sales Office : Qingpu
Tel   86-21-3920-2988
Material
Cust.(Mat.)
Material
Commodity
Ctry/Reg
Qty.
UOM
Unit price
Total
Code
Code
Description
Code
Origin
Ship
value
Shipment Date                 30.01.2026
Invoice Date                  30.01.2026
Invoice No.
P.O.No               PO845487
Incoterms            Ex works/Collect
SHANGHAI
Payment Terms        0 Days Net (Interco)
Carrier              CUSTOMER PICK UP
Ship Cond            LTL
Shipment No.         0024035516-0002
Special Instructions
501656989
SEALED AIR PACKAGING MATERIALS (I)
245 8TH MAIN, 3RD PHASE
PEENYA INDUSTRIAL AREA
560058 BANGALORE
INDIA
Invoice to   C831
1  of  1
SEALED AIR PACKAGING MATERIALS
(INDIA) LLP
20 CUBE WHSING & DISTRIBUTION PVT LT
SY NO.55/1,HUSKUR MAIN ROAD
562123 BANGALORE KARNATAKA
Ship To   1595061
PAN NUMBER: ADJFS5047D
245, 8TH MAIN, 3RD PHASE
560058 BANGALORE
INDIA
Sold to   P5031
"""

async def verify_fix():
    print("--- 🚀 Testing Double-Detection Fix ---")
    print(f"Input Length: {len(RAW_TEXT_SAMPLE)} chars")
    
    result = await extract_with_hybrid_engine(RAW_TEXT_SAMPLE)
    
    docs = result.get("documents", [])
    print(f"--- Found {len(docs)} document(s) ---")
    
    for i, doc in enumerate(docs):
        print(f"\nDocument {i+1}:")
        print(f"Type: {doc.get('document_type')}")
        print(f"Data: {json.dumps(doc.get('structured_data'), indent=2)}")
        print(f"Confidence: {doc.get('confidence_score')}")

    if len(docs) == 1:
        data = docs[0].get("structured_data", {})
        if data.get("invoice_date") and data.get("invoice_number"):
            print("\n✅ SUCCESS: Single-page invoice unified correctly!")
        elif data.get("invoice_date") or data.get("invoice_number"):
            print("\n⚠️ PARTIAL: Only one doc found, but fields missing.")
        else:
            print("\n❌ FAIL: Single doc found but both key fields missing.")
    else:
        print(f"\n❌ FAIL: Found {len(docs)} docs instead of 1.")

if __name__ == "__main__":
    asyncio.run(verify_fix())
