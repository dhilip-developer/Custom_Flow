"""
Agent 2: Bill of Lading Extractor (AI-Powered Deep Analysis)

Hybrid engine that uses LLM (GPT-4o-mini) for semantic 'Document AI' analysis 
if an API key is present, otherwise falls back to robust local Regex heuristics.
"""

from __future__ import annotations
import re
import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load API keys from .env if present
load_dotenv()

def is_ai_enabled() -> bool:
    """Checks if a valid OpenAI API key is configured."""
    key = os.getenv("OPENAI_API_KEY")
    return bool(key and len(key) > 10)

def extract_expanded_bol(text: str) -> Dict[str, Any]:
    """
    Main extraction entry point. Tries AI first (if configured), then Local Regex.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key and len(api_key) > 10:
        try:
            return _extract_via_ai(text, api_key)
        except Exception as exc:
            print(f"AI Extraction failed ({exc}), falling back to local Regex...")
            return _extract_via_regex(text)
    else:
        return _extract_via_regex(text)

def _extract_via_ai(text: str, api_key: str) -> Dict[str, Any]:
    """
    Uses OpenAI GPT-4o-mini to perform semantic 'Document AI' extraction.
    """
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a specialized Shipping Document AI (Agent 2). 
    Your task is to extract exactly 14 fields from raw, noisy Bill of Lading (BOL) text.
    
    REQUIRED JSON SCHEMA:
    {
        "BILL NO.": "String",
        "BILL DATE": "String",
        "CONSIGNEE/ RECIEVER": "String (Full Address/Company)",
        "IMPORTER /SUPPLIER": "String (Full Address/Company)",
        "PORT OF LOADING": "String",
        "PORT OF DISCHARGE": "String",
        "TYPE OF MOVEMENT": "String (e.g. FCL/FCL, LCL/LCL)",
        "CONTAINER NUMBER": "String",
        "PACKAGE": "String",
        "MEASUREMENTS": "String",
        "GROSS WEIGHT": "String",
        "FREIGHT COLLECT": "PREPAID or COLLECT",
        "DESCRIPTION OF GOODS": "String",
        "HS CODE": "String"
    }

    RULES:
    1. If a field is missing, strictly return "Not Found in Text".
    2. Maintain the casing of addresses.
    3. Return ONLY the raw JSON object. No markdown. No conversational text.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RAW BOL TEXT:\n{text}"}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        content = response.choices[0].message.content
        return json.loads(content)
    except:
        raise ValueError("Invalid JSON response from AI")

def _extract_via_regex(text: str) -> Dict[str, Any]:
    """
    Robust local Regex engine (Heuristic Fallback).
    """
    text_clean = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
    text_upper = text_clean.upper()
    
    payload = {
        "BILL NO.": "",
        "BILL DATE": "",
        "CONSIGNEE/ RECIEVER": "",
        "IMPORTER /SUPPLIER": "",
        "PORT OF LOADING": "",
        "PORT OF DISCHARGE": "",
        "TYPE OF MOVEMENT": "",
        "CONTAINER NUMBER": "",
        "PACKAGE": "",
        "MEASUREMENTS": "",
        "GROSS WEIGHT": "",
        "FREIGHT COLLECT": "",
        "DESCRIPTION OF GOODS": "",
        "HS CODE": ""
    }
    
    # 1. Split Boundaries into Formal Labels vs Unit Markers
    FORMAL_LABELS = r'BILL OF LADING|B/L|BILL NO|DATE|ISSUED|CONSIGNEE|RECEIVER|NOTIFY|PARTY|SHIPPER|SUPPLIER|EXPORTER|PORT OF|POL|POD|DESTINATION|DELIVERY|RECEIPT|CONTAINER|CNTR|GROSS WEIGHT|WEIGHT|NET WEIGHT|G\.W|VOLUME|MEASUREMENT|MEAS|PACKAGE|PKGS|FREIGHT|MOVE|CY/CY|CFS/CFS|FCL|LCL|TOTAL|LADEN|INCOTERM|PHONE|FAX|CONSOL NO|IEC NO|PAN NO|HS CODE|H\.S\. CODE|DESCRIPTION|GOODS|DETAILS|MARKS|COMMODITY|KIND OF'
    UNITS_MARKERS = r'KGS|LBS|CBM|M3|PALLETS|CARTONS|CTNS|CTN|PO NO|PO#|REF NO|INVOICE|INV'
    
    # Standard boundary strictly cuts at labels OR units
    STRICT_BOUNDARIES = r'(?=\b(?:' + FORMAL_LABELS + r'|' + UNITS_MARKERS + r')\b|$)'
    
    # Loose boundary only cuts at FORMAL labels (allows swallowing units/description)
    LOOSE_BOUNDARIES = r'(?=\b(?:' + FORMAL_LABELS + r')\b|$)'

    def extract_bounded(pattern: str, strict: bool = True) -> str:
        anchor = r'\b(?:' + pattern + r')\b'
        bound = STRICT_BOUNDARIES if strict else LOOSE_BOUNDARIES
        match = re.search(anchor + r'[\s\:]+(.*?)' + bound, text_upper, re.DOTALL)
        if match:
            res = match.group(1).strip()
            res = re.sub(r'[\s,]+$', '', res)
            return res
        return ""

    # Field Extractions
    payload["BILL NO."] = extract_bounded(r'B/L NO|BILL OF LADING NO|BL NO|BILL NO|B/L|AWB|WAYBILL', strict=False)
    payload["BILL DATE"] = extract_bounded(r'DATE|ISSUED|LADEN ON BOARD|SHIPPED ON BOARD', strict=False)

    payload["CONSIGNEE/ RECIEVER"] = extract_bounded(r'CONSIGNEE|RECEIVER|NOTIFY PARTY|TO', strict=False)
    payload["IMPORTER /SUPPLIER"] = extract_bounded(r'SHIPPER|SUPPLIER|EXPORTER|FROM', strict=False)
    payload["PORT OF LOADING"] = extract_bounded(r'PORT OF LOADING|POL|PLACE OF RECEIPT|PORT OF RECEIPT|LOAD PORT', strict=True)
    payload["PORT OF DISCHARGE"] = extract_bounded(r'PORT OF DISCHARGE|POD|DESTINATION|FINAL DESTINATION|PLACE OF DELIVERY|DISCHARGE PORT', strict=True)

    # Standard metrics (use strict to avoid overlap)
    payload["GROSS WEIGHT"] = extract_bounded(r'GROSS WEIGHT|WEIGHT|G\.W\.', strict=True)
    payload["MEASUREMENTS"] = extract_bounded(r'VOLUME|MEASUREMENT|MEAS|SIZE', strict=True)
    payload["PACKAGE"] = extract_bounded(r'PACKAGE|PKGS|NO\. OF PKGS|TOTAL PKGS|QUANTITY', strict=True)

    # 13. HS CODE Capture with LOOSE boundaries (deliberate leak)
    hs_leak = ""
    # Use LOOSE to ensure we capture the following line even if it has no 'DESCRIPTION:' label
    hs_raw = extract_bounded(r'HS CODE|H\.S\. CODE|HARMONIZED CODE|COMMODITY CODE|HTS CODE', strict=False)
    if hs_raw:
        hs_split_match = re.search(r'^([\d\.]{4,15})(.*)', hs_raw, re.DOTALL)
        if hs_split_match:
            payload["HS CODE"] = hs_split_match.group(1).strip()
            hs_leak = hs_split_match.group(2).strip()
        else:
            payload["HS CODE"] = hs_raw

    # RECURSIVE RECOVERY: Hunt for missing data in the HS leak
    if hs_leak:
        if not payload["GROSS WEIGHT"] or payload["GROSS WEIGHT"] == "Not Found in Text":
            gw_rec = re.search(r'([\d,]+(?:\.\d+)?\s*(?:KGS|KG|LBS|MT|TONS|TON))', hs_leak)
            if gw_rec: payload["GROSS WEIGHT"] = gw_rec.group(1)
        
        if not payload["PACKAGE"] or payload["PACKAGE"] == "Not Found in Text":
            pkg_rec = re.search(r'([\d,]+\s*(?:TOTE|CTN|PKG|PKGS|CARTONS|PALLETS|UNITS|PCS|PIECES|BOXES|BAGS|ROLLS))', hs_leak)
            if pkg_rec: payload["PACKAGE"] = pkg_rec.group(1)

        if not payload["MEASUREMENTS"] or payload["MEASUREMENTS"] == "Not Found in Text":
            ms_rec = re.search(r'([\d,]+(?:\.\d+)?\s*(?:CBM|M3|FT3|CUFT))', hs_leak)
            if ms_rec: payload["MEASUREMENTS"] = ms_rec.group(1)

        # Remaining text logic
        clean_desc = hs_leak
        for val in [payload["GROSS WEIGHT"], payload["PACKAGE"], payload["MEASUREMENTS"]]:
            if val and val != "Not Found in Text":
                clean_desc = clean_desc.replace(val, "")
        
        clean_desc = re.sub(r'(?:PO NO|PO#|REF NO|INVOICE|INV|[:\s\=/=])+', ' ', clean_desc).strip()
        if clean_desc and not payload["DESCRIPTION OF GOODS"]:
            payload["DESCRIPTION OF GOODS"] = clean_desc

    # Fallback to standard capture if still missing
    if not payload["DESCRIPTION OF GOODS"]:
        payload["DESCRIPTION OF GOODS"] = extract_bounded(r'DESCRIPTION OF GOODS|DESCRIPTION|GOODS|CARGO|COMMODITY|DETAILS|MARKS|KIND OF', strict=False)

    # Formatting Cleanup
    for k, v in payload.items():
        if v:
            if k not in ["CONTAINER NUMBER", "FREIGHT COLLECT", "TYPE OF MOVEMENT", "HS CODE"]:
                payload[k] = v.strip().title() if len(v.split()) < 4 else v.strip()
        else:
            payload[k] = "Not Found in Text"

    return payload
