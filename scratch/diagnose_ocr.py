"""
Quick diagnostic — why is the regex engine failing on real OCR text?
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW = """\n\nⒸ SEE\nINVOICE\nSales Office: Qingpu\nTel\n86-21-3920-2988\nSEALED AIR (CHINA) CO., LTD.\n6988 SONGZE AVENUE\nQINGPU INDUSTRIAL PARK SHANGHAI 201705\nChina\nTel: 86-21-3920-2988\nFax: 86-21-3920-2980\nSEALED AIR PACKAGING MATERIALS (I)\n245 8TH MAIN, 3RD PHASE\nPEENYA INDUSTRIAL AREA\n560058 BANGALORE\nINDIA\nSEALED AIR PACKAGING MATERIALS\n(INDIA) LLP\nSEALED AIR PACKAGING MATERIALS (I)\nPAN NUMBER: ADJFS5047D\n20 CUBE WHSING & DISTRIBUTION PVT LT 245, 8TH MAIN, 3RD PHASE\nSY NO.55/1, HUSKUR MAIN ROAD\n562123 BANGALORE KARNATAKA\n560058 BANGALORE\nINDIA\nInvoice to C831\nShip To 1595061\nSold to\nP5031\nInvoice No.\nP.O.No\nIncoterms\nPayment Terms\nCarrier\nShip Cond\nShipment No.\nShipment Date\nInvoice Date\n501656989\nPO845487\nEx works/Collect\nSHANGHAI\n0 Days Net (Interco)\nCUSTOMER PICK UP\nLTL\n0024035516-0002\n30.01.2026\n30.01.2026\nSpecial Instructions\nMaterial\nCode\n101095556\nCust. (Mat.)\nCode\nMaterial\nDescription\nB210 CB 165X300 STD\nSEUT B NA7AQ\nCommodity\nCode\nCtry/Reg\nOrigin\nQty.\nShip\nUOM\nUnit price\nTotal\nvalue\n3923210000\nCN\n20.600\nMU\nUSD 48.78883\nUSD\n1,005.05\nSAQA3264 B82-1KG Pizza Cheese Moz165x300\nNote: Tax1 = VAT\nComputer Generated Invoice: No Signature Required\n1 of 1\nTotal net value\nUSD\nUSD\n1,005.05\n0.00\nTotal Freight\nTotal Tax1\nTotal Tax\nDownpayment\nTOTAL\nUSD\nUSD\n0.00\n1,005.05\n"""

# Print line-by-line with numbers to see the structure
lines = RAW.split("\n")
print("=== LINE-BY-LINE ANALYSIS ===")
for i, line in enumerate(lines):
    print(f"  L{i:3d}: '{line}'")

# Expected correct extraction:
print("\n=== EXPECTED CORRECT VALUES ===")
print("  invoice_number:  501656989")
print("  invoice_date:    30.01.2026")
print("  po_number:       PO845487")
print("  buyer_name:      SEALED AIR PACKAGING MATERIALS (INDIA) LLP")
print("  seller_name:     SEALED AIR (CHINA) CO., LTD.")
print("  total_amount:    1005.05")
print("  currency:        USD")
print("  hsn_code:        3923210000")
print("  pan_number:      ADJFS5047D")
print("  incoterms:       Ex works")
print("  item:            B210 CB 165X300 STD, Qty 20.600, Unit USD 48.78883, Total USD 1,005.05")
