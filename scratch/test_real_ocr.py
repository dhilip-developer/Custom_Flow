"""Test the regex engine against real OCR output from Agent 1."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction_engine import extract_structured_data

RAW_TEXT = "\n\nⒸ SEE\nINVOICE\nSales Office: Qingpu\nTel\n86-21-3920-2988\nSEALED AIR (CHINA) CO., LTD.\n6988 SONGZE AVENUE\nQINGPU INDUSTRIAL PARK SHANGHAI 201705\nChina\nTel: 86-21-3920-2988\nFax: 86-21-3920-2980\nSEALED AIR PACKAGING MATERIALS (I)\n245 8TH MAIN, 3RD PHASE\nPEENYA INDUSTRIAL AREA\n560058 BANGALORE\nINDIA\nSEALED AIR PACKAGING MATERIALS\n(INDIA) LLP\nSEALED AIR PACKAGING MATERIALS (I)\nPAN NUMBER: ADJFS5047D\n20 CUBE WHSING & DISTRIBUTION PVT LT 245, 8TH MAIN, 3RD PHASE\nSY NO.55/1, HUSKUR MAIN ROAD\n562123 BANGALORE KARNATAKA\n560058 BANGALORE\nINDIA\nInvoice to C831\nShip To 1595061\nSold to\nP5031\nInvoice No.\nP.O.No\nIncoterms\nPayment Terms\nCarrier\nShip Cond\nShipment No.\nShipment Date\nInvoice Date\n501656989\nPO845487\nEx works/Collect\nSHANGHAI\n0 Days Net (Interco)\nCUSTOMER PICK UP\nLTL\n0024035516-0002\n30.01.2026\n30.01.2026\nSpecial Instructions\nMaterial\nCode\n101095556\nCust. (Mat.)\nCode\nMaterial\nDescription\nB210 CB 165X300 STD\nSEUT B NA7AQ\nCommodity\nCode\nCtry/Reg\nOrigin\nQty.\nShip\nUOM\nUnit price\nTotal\nvalue\n3923210000\nCN\n20.600\nMU\nUSD 48.78883\nUSD\n1,005.05\nSAQA3264 B82-1KG Pizza Cheese Moz165x300\nNote: Tax1 = VAT\nComputer Generated Invoice: No Signature Required\n1 of 1\nTotal net value\nUSD\nUSD\n1,005.05\n0.00\nTotal Freight\nTotal Tax1\nTotal Tax\nDownpayment\nTOTAL\nUSD\nUSD\n0.00\n1,005.05\n"

result = extract_structured_data(RAW_TEXT)

print("\n" + "=" * 70)
print("  RESULTS")
print("=" * 70)
for doc in result.documents:
    print(f"\n--- {doc.document_type.upper()} ---")
    print(json.dumps(doc.structured_data, indent=2, default=str))

# Validate against expected
print("\n" + "=" * 70)
print("  ACCURACY CHECK")
print("=" * 70)
EXPECTED = {
    "invoice_number": "501656989",
    "invoice_date": "30/01/2026",
    "po_number": "PO845487",
    "total_amount": 1005.05,
    "currency": "USD",
}

if result.documents:
    data = result.documents[0].structured_data
    for key, expected in EXPECTED.items():
        actual = data.get(key)
        match = str(actual) == str(expected) or actual == expected
        icon = "✓" if match else "✗"
        print(f"  {icon} {key}: expected={expected}, got={actual}")
else:
    print("  ✗ NO DOCUMENTS EXTRACTED")

if __name__ == "__main__":
    pass
