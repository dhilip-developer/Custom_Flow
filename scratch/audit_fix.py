import asyncio
import sys
import os

# Set up paths
sys.path.append(os.getcwd())

from services.intelligence_utils import extract_with_super_agent, SuperExtractionResponse

# The exact text snippet from the user's CURL
MOCK_TEXT = """
Billed to:
Consigneed to:
Invoice / Bill of Supply
Cov03031
1/3 Original for Recipient\\Transporter\\Supplier\\Extra
Invoice No.: MH2536000682
Date/Time 24.02.2026 / 12:03:53
PNR NO.: 11188791
SEALED AIR PACKAGING MATERIALS (INDIA)LLP
PLOT NO. 245, 8TH MAIN, 3RD PHASE,
560058 PEENYA II PHASE, IND. AREA, BANGALORE
Covestro (India) Private Limited
NH-160,Building B600,K-Square Industrial
Warehousing Park, Mumbai-Nashik Highway,
Tal.Bhiwandi,Kurund
MAHARASTRA 421101
Maharashtra, India
Karnataka, India GSTN No. 29ADJFS5047D1ZW
PNR NO.: 11518844
SEALED AIR PACKAGING MATERIALS (INDIA)LLP
SF NO.200/1B, Kulswamini Industries
602106 SIPCOT INDUSTRIAL PARK SRIPRUMBUDUR
OM Logistics OPP SIDE ROAD, SIRUMANGADU
Tamil Nadu, India GSTN No. 33ADJFS5047D1Z7
GST No. 27AAACB2419H1Z0
Tax is Payable on Reverse Charge: No
PAN: AAACB2419H
CIN: U19113MH1995PTC179724
Place of Supply :Karnataka -29
Place of Delivery :Tamil Nadu -33
P.O. No. & Date: PO845501 / 13.01.2026
Sales Contract No. & Date: 3015127637 / 13.01.2026
Payment Due Date: 10.05.2026
Transporter:
Mode of Transport: Truck
Destination: SIPCOT Industrial Park Sriprumbudur
Original invoice number:
LR No.:
LR Date:
Vehicle No.:
Product Code
HSN/SAC Code
U/M
Product Description
No. of Packs
Quantity
Batches
04343313
39093100 INSTAPAK CHEMICAL A 0250.00 KG B13
KG
20,000.000
Remarks / Special Instructions
Words
Invoice Value:
GST
Covestro
Unit Price (Rs.) Assessable Value (Rs.)
151.64
3.032,800.00
60
80
U7AA241053
Net Amount
3.032,800.00
Total GST:
0.00
Total Amount including GST:
Total Amount include TCS:
3,032,800.00
3,032,800.00
RUPEES THIRTY LAC THIRTY-TWO THOUSAND EIGHT HUNDRED:
Covestro
"""

async def run_audit():
    print("--- STARTING AUDIT OF USER PAYLOAD ---")
    response = await extract_with_super_agent(MOCK_TEXT)
    
    for doc in response.documents:
        data = doc.structured_data
        print(f"\nDocument: {doc.document_type}")
        print(f"ID: {data.get('invoice_number')}")
        print(f"GST Seller: {data.get('gst_number')}")
        print(f"Place of Supply: {data.get('place_of_supply')}")
        print(f"Items Count: {len(data.get('items', []))}")
        if data.get('items'):
            print(f"First Item: {data['items'][0]['name']}")
    
    print("\n--- AUDIT COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_audit())
