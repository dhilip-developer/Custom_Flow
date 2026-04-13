"""
Test script for the regex extraction engine.
Uses synthetic OCR-like text to validate all 5 extractors.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction_engine import extract_structured_data

# Simulated Agent 1 output — merged raw text with === delimiters
SAMPLE_RAW_TEXT = """
COMMERCIAL INVOICE
Invoice No.: INV-2026-0457
Invoice Date: 07/04/2026
Buyer: M/S Global Imports Pvt Ltd
Seller: Covestro Deutschland AG
GSTIN: 33AABCU9603R1ZM
P.O. Number: PO-2026-1122
P.O. Date: 01/04/2026
Place of Supply: Tamil Nadu
Place of Delivery: Chennai Port

Sr No  Description         HSN Code   Qty    Unit Price   Amount
1      Polycarbonate Resin  39074000   500    USD 6,065.60  USD 3,032,800.00
2      Makrolon 2405        39074000   200    USD 5,200.00  USD 1,040,000.00

Total Amount: USD 4,072,800.00
Currency: USD

Terms and Conditions apply. Authorised Signatory.

==================================================

BILL OF LADING
B/L No.: HLCUHAM260300389
B/L Date: 05/04/2026
Shipper: Covestro Deutschland AG, Leverkusen, Germany
Consignee: To Order of HDFC Bank Ltd
Notify Party: M/S Global Imports Pvt Ltd, Chennai
Vessel Name: MV EVER GOLDEN
Voyage No.: 0234E
Port of Loading: HAMBURG, GERMANY
Port of Discharge: CHENNAI, INDIA
Container Number: HLXU8073652
Seal Number: SL-78234
Gross Weight: 21,749.200 KGS
Net Weight: 21,500.000 KGS
700 Packages
Freight Prepaid

Description of Goods: POLYCARBONATE RESIN IN BAGS

==================================================

PACKING LIST
Packing List No.: PL-2026-0457
Date: 07/04/2026
Total Packages: 700
Gross Weight: 21,749.200 KGS
Net Weight: 21,500.000 KGS
Marks and Numbers: MK/GI/2026/CHN
Total CBM: 45.6

Sr No  Description          Qty     Net Wt    Gross Wt
1      Polycarbonate Resin  500     15500.00  15600.00
2      Makrolon 2405        200     6000.00   6149.20

==================================================

HIGH SEAS SALE AGREEMENT
HSS Agreement Ref No.: HSS/2026/04/0089
Dated: 07/04/2026
Seller (Transferor): M/S Global Imports Pvt Ltd
Buyer (Transferee): M/S Polymer Industries Ltd
B/L Number: HLCUHAM260300389
Vessel Name: MV EVER GOLDEN
Port of Loading: HAMBURG, GERMANY
Port of Destination: CHENNAI, INDIA
Foreign Invoice No.: INV-2026-0457
Foreign Invoice Date: 07/04/2026
Foreign Invoice Amount: USD 4,072,800.00
Currency: USD
Incoterms: CIF
Buyer P.O. Number: BPO/2026/PIX-445
Buyer P.O. Date: 02/04/2026

==================================================

FREIGHT CERTIFICATE
HBL No.: HLCUHAM260300389
Vessel: MV EVER GOLDEN
Container No.: HLXU8073652
Total Freight Amount: USD 12,500.00
Ocean Freight: USD 10,000.00
Local Charges: USD 1,500.00
Terminal Handling: USD 1,000.00
Packages: 700
Weight: 21,749.200 KGS
Description of Goods: POLYCARBONATE RESIN IN BAGS
"""


def main():
    print("=" * 70)
    print("  REGEX EXTRACTION ENGINE TEST")
    print("=" * 70)

    result = extract_structured_data(SAMPLE_RAW_TEXT)

    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {len(result.documents)} documents extracted")
    print(f"{'=' * 70}\n")

    for doc in result.documents:
        print(f"\n--- {doc.document_type.upper()} ---")
        print(json.dumps(doc.structured_data, indent=2, default=str))

    # Validation checks
    print(f"\n{'=' * 70}")
    print("  VALIDATION")
    print(f"{'=' * 70}")

    doc_types = [d.document_type for d in result.documents]
    expected_types = ["invoice", "bill_of_lading", "packing_list", "high_seas_sale_agreement", "freight_certificate"]

    for expected in expected_types:
        status = "✓" if expected in doc_types else "✗"
        print(f"  {status} {expected}")

    # Check specific field values
    for doc in result.documents:
        data = doc.structured_data
        if doc.document_type == "invoice":
            assert data.get("invoice_number"), "Invoice number missing!"
            assert data.get("total_amount"), "Total amount missing!"
            print(f"  ✓ Invoice: #{data['invoice_number']}, Amount={data['total_amount']}")
        elif doc.document_type == "bill_of_lading":
            assert data.get("bl_number"), "BL number missing!"
            assert data.get("vessel_name"), "Vessel name missing!"
            assert data.get("container_number"), "Container number missing!"
            print(f"  ✓ BOL: #{data['bl_number']}, Vessel={data['vessel_name']}, Container={data['container_number']}")
        elif doc.document_type == "packing_list":
            assert data.get("total_packages"), "Total packages missing!"
            assert data.get("gross_weight"), "Gross weight missing!"
            print(f"  ✓ PL: Packages={data['total_packages']}, GW={data['gross_weight']}")
        elif doc.document_type == "high_seas_sale_agreement":
            assert data.get("hss_ref_no"), "HSS ref missing!"
            assert data.get("buyer"), "Buyer missing!"
            print(f"  ✓ HSS: #{data['hss_ref_no']}, Buyer={data['buyer']}")
        elif doc.document_type == "freight_certificate":
            assert data.get("bl_number"), "Freight BL number missing!"
            assert data.get("total_amount"), "Freight amount missing!"
            print(f"  ✓ FC: BL={data['bl_number']}, Amount={data['total_amount']}")

    print(f"\n{'=' * 70}")
    print("  ALL TESTS PASSED ✓")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
