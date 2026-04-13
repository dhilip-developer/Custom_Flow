"""
Enhanced text extraction and heuristic module for Expert Analysis.

Extracts detailed data points from raw text (Sellers, Buyers, Dates, Ports)
to build a comprehensive ShippingDocuments payload.
"""

from typing import Dict, Any, List
import io
import re

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


def extract_data_from_text(text: str) -> Dict[str, Any]:
    """
    Applies heuristics to find detailed fields in plain text.
    Returns a dictionary conforming to the ShippingDocuments schema.
    """
    text_upper = text.upper()
    lines = text.split('\n')
    
    # ── Heuristics ──────────────────────────────────────────────

    # 1. Incoterm
    incoterms_list = ["CIF", "FOB", "EXW", "CFR", "FAS", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP"]
    found_incoterm = "Unknown"
    for term in incoterms_list:
        if re.search(r'\b' + term + r'\b', text_upper):
            found_incoterm = term
            break
            
    # 2. Insurance Detect (Smarter to avoid negations like "No Insurance")
    insurance_present = False
    if "INSURANCE" in text_upper or "INS" in text_upper:
        # Check for proximity of negation words
        negations = ["NO ", "NONE", "NOT FOUND", "MISSING", "N/A", "WITHOUT"]
        is_negated = False
        # Simple check: if a negation word appears shortly before "INSURANCE"
        for neg in negations:
            # Look for negation within 20 chars before "INSURANCE"
            idx = text_upper.find("INSURANCE")
            if idx == -1: idx = text_upper.find("INS ")
            
            start = max(0, idx - 20)
            context = text_upper[start:idx]
            if neg in context:
                is_negated = True
                break
        
        if not is_negated:
            insurance_present = True
    
    # 3. Value & Charges
    total_value = 0.0
    value_match = re.search(r'TOTAL VALUE\D*[:\- ]*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text_upper)
    if not value_match:
        value_match = re.search(r'AMOUNT\D*[:\- ]*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text_upper)
    
    if value_match:
        try:
            total_value = float(value_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # 4. Dates
    date_match = re.search(r'DATE\D*[:\- ]*([\d]{1,4}[-/.][\d]{1,2}[-/.][\d]{1,4})', text_upper)
    extracted_date = date_match.group(1) if date_match else "2026-03-31"

    # 5. Names (Seller/Buyer/Consignee)
    seller = "SELLER NOT FOUND"
    buyer = "BUYER NOT FOUND"
    consignee = "CONSIGNEE NOT FOUND"
    
    # Simple multi-line lookups
    lines_trimmed = [l.strip() for l in lines if l.strip()]
    for i, line in enumerate(lines_trimmed):
        if "SELLER" in line.upper() or "SHIPPER" in line.upper():
            if i + 1 < len(lines_trimmed): seller = lines_trimmed[i+1]
        if "BUYER" in line.upper() or "SOLD TO" in line.upper():
            if i + 1 < len(lines_trimmed): buyer = lines_trimmed[i+1]
        if "CONSIGNEE" in line.upper():
            if i + 1 < len(lines_trimmed): consignee = lines_trimmed[i+1]

    # 6. Ports
    pol = "POL NOT FOUND"
    pod = "POD NOT FOUND"
    pol_match = re.search(r'PORT OF LOADING\D*[:\- ]*([^\n\r,]+)', text_upper)
    pod_match = re.search(r'PORT OF DISCHARGE\D*[:\- ]*([^\n\r,]+)', text_upper)
    if pol_match: pol = pol_match.group(1).strip().title()
    if pod_match: pod = pod_match.group(1).strip().title()

    # 7. Invoice/BL numbers
    inv_num = "INV-0000"
    bl_num = "BL-0000"
    inv_match = re.search(r'INVOICE NO\D*[:\- ]*([A-Z0-9\-]+)', text_upper)
    bl_match = re.search(r'B/L NO\D*[:\- ]*([A-Z0-9\-]+)', text_upper)
    if inv_match: inv_num = inv_match.group(1)
    if bl_match: bl_num = bl_match.group(1)

    # ── Mocked Payload Construction ──────────────────────────────
    payload = {
        "invoice": {
            "invoice_number": inv_num,
            "seller": seller,
            "buyer": buyer,
            "date": extracted_date,
            "incoterm": found_incoterm,
            "total_value": total_value or 50000.0,
            "currency": "USD",
            "insurance_charges": 500.0 if insurance_present else None,
            "insurance_reference": "REF-INS-99" if insurance_present else None,
            "line_items": [
                {
                    "description": "Expert Extracted Goods",
                    "quantity": 100, # Mocked quantity for cross-check demos
                    "unit_price": total_value/100 if total_value > 0 else 500,
                    "total": total_value or 50000.0
                }
            ]
        },
        "packing_list": {
            "packing_list_number": inv_num.replace("INV", "PL"),
            "total_packages": 10,
            "declared_value": total_value or 50000.0
        },
        "bill_of_lading": {
            "bol_number": bl_num,
            "shipper": seller,
            "consignee": consignee if consignee != "CONSIGNEE NOT FOUND" else buyer,
            "port_of_loading": pol,
            "port_of_discharge": pod,
            "vessel_name": "Expert Carrier Vessel",
            "incoterm": found_incoterm,
            "insurance_reference": "REF-INS-99" if insurance_present else None
        }
    }
    
    return payload


def extract_data_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts text from a PDF using PyPDF2 and passes it to the expert text extractor.
    """
    text = ""
    if PyPDF2:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            print(f"Failed to extract text from PDF: {e}")
    else:
        text = pdf_bytes.decode("utf-8", errors="ignore")
        
    return extract_data_from_text(text)
