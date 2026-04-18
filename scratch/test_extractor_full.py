import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.extraction_engine import extract_structured_data

raw_data = """
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
'Covestro' &
are the trademark of
Covestro Deutschland AG
For Industrial use Only - Not for Retail Sale
Signature valid
Digitally signed by DS COVESTRO INDIA) PRIVATE LIMITED 1
Date: 2026.02.24 04:53:45 PM 05:30
Authorized By Mehernosh Patel
* This invoice is governed by and subjected to the General Terms and Conditions attached with this invoice separately and the
same shall be considered as a part & parcel of this invoice.
Registered Office: Unit No. SB-801, 8th Floor, Empire Tower, Cloud City Campus, Airoli, Thane - Belapur Rd,
Navi Mumbai, Thane - 400 708, Maharashtra, India. Board no. +91-2268195555 Fax no. +91-2268195556
I.
1.
*Details of the relevant invoice - invoice date: 24.02.2026
General
2/3 Original for Recipient\\Transporter\\Supplier\\Extra
The risk of the goods shall pass to the Buyer upon delivery in accordance with the agreed trade
terms,
These General Conditions of Sale and Delivery ("General Conditions") shall govern and be
incorporated into every contract for the sale and purchase of goods between Covestro (India) Private
Limited (the "Seller") and the buyer of goods (the "Buyer"). unless they are expressly varied by a
separate written contract between the parties. Any general terms and conditions of purchase or
other reservations made by the Buyer shall not be effective unless the Seller has expressly accepted
them in
in
writing for a particular order.

==================================================

I.
1.
*Details of the relevant invoice - invoice date: 24.02.2026
General
2/3 Original for Recipient\\Transporter\\Supplier\\Extra
The risk of the goods shall pass to the Buyer upon delivery in accordance with the agreed trade
terms,
These General Conditions of Sale and Delivery ("General Conditions") shall govern and be
incorporated into every contract for the sale and purchase of goods between Covestro (India) Private
Limited (the "Seller") and the buyer of goods (the "Buyer"). unless they are expressly varied by a
separate written contract between the parties. Any general terms and conditions of purchase or

==================================================

Ref: HSS/COV03031/2025-26
To,
SEALED AIR PACKAGING MATERIALS (INDIA) LLP
PLOT NO. 245, 8TH MAIN, 3RD PHASE, PEENYA II PHASE, IND. AREA,
BANGALORE - 560058, KARNATAKA, INDIA
Sub: Sub: Sale of Goods on High Sea Sale Agreement Basis:
Product Description:
covestro
Date: 24-02-2026
Sr.
Item
No Description
UoM
Gross
Weight Weight
Net
Packages
Local
Invoice
No.
Local
Invoice
date
B/L Number BL date
Covestro (India) Pvt. Ltd.
INSTAPAK
PALLETS
CHEMICAL A
KGS 21,749.200 20,000.000 STC 80
0250,00 KG
B13
MH253600
0682
24-02-2026
ONEYSH5A
CFU90900
17-02-2026
STEEL
DRUMS

==================================================

To,
THE ASST./DY. COMMISSIONER OF CUSTOMS
CUSTOMS HOUSE, 60, RAJAJI SALAI, CHENNAI -
600001, TAMILNADU
Product Description:
covestro
Date: 24-02-2026

==================================================

To,
OCEAN NETWORK EXPRESS LINE (INDIA) PVT. LTD. (CHENNAI)
SKCL ICON, C-42 & C-43, CIPET RD, THIRU-VI-KA
INDUSTRIAL ESTATE, GUINDY, CHENNAI, TAMIL NADU
600032. TEL: 4461414200
Product Description:
covestro

==================================================

SPX.
00500
भारतीय गैर न्यायिक
भारत INDIA
रु.500
पाँच सौ रुपये
05005
005005
सत्यमेव जयते
INDIA NON

==================================================

Covestro (India) Private Limited
SB-801, 8th Floor, EMPIRE TOWER,
400708 NAVI MUMBAI AIROLI
INDIA
Invoice
No. 8526011824

==================================================

Delivery address:
FG Warehouse
NH160, BUILDING B600,K-SQUARE INDUSTRIAL
&WAREHOUSING PARK, MUMBAI-NASIK HIGHWAY,
TAL. BHIWANDI, KURUND, THANE
421101 MAHARASTRA-THANE
INDIA

==================================================

covestro
INDIA
No.82 Muhua Road
201507 SHANGHAI
PR OF CHINA
Weight Note

==================================================

Delivery to:
FG Warehouse
NH160, BUILDING B600.K-SQUARE INDUSTRIAL
INDIA
No.82 Muhua Road
201507 SHANGHAI
PR OF CHINA
Certification Of Origin
Invoice
8526011824

==================================================

Certificate of Analysis
FG Warehouse
INDIA
Product name
INSTAPAK CHEMICAL A 0250,00 KG B13

==================================================

ONE
OCEAN NETWORK EXPRESS
ORIGINAL NON NEGOTIABLE
PAGE:
1 OF
SEA WAYBILL

==================================================

Importer-Exporter Code
IEC
This is to certify that COVESTRO (INDIA) PRIVATE LIMITED is issued an
Importer-Exporter Code (IEC) 0396009662 with details as follows

==================================================

Form GST REG-06
[See Rule 10(1)]
Registration Certificate
Registration Number :27AAACB2419H1Z0

==================================================

Letter of Authority
We, Covestro (India) Private Limited, CIN: U19113MH1995PTC179724 a company

"""

print("Running pure-Python extraction...")
response = extract_structured_data(raw_data)

print(json.dumps([doc.dict() for doc in response.documents], indent=2, default=str))

