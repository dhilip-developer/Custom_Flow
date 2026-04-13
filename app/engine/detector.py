"""
Insurance Requirement Detection Engine – AI-Powered & Heuristic.

Implements the rule-based logic to determine whether an Insurance Certificate
is required and provides specific, human-readable reasons and confidence scores.
Includes a hybrid "Document AI" mode using GPT-4o-mini for complex, noisy text.
"""

from __future__ import annotations
import os
import json
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from shared.insurance_app.models.schemas import ShippingDocuments, AgentResult

# Load API keys from .env if present
load_dotenv()

def is_ai_enabled() -> bool:
    """Checks if a valid OpenAI API key is configured."""
    key = os.getenv("OPENAI_API_KEY")
    return bool(key and len(key) > 4)

def detect_insurance_requirement(docs: ShippingDocuments) -> AgentResult:
    """
    Standard Rule-based logic (Heuristic Fallback).
    """
    inv = docs.invoice
    bol = docs.bill_of_lading
    
    # Identify Incoterm
    incoterm = (inv.incoterm or bol.incoterm or "Unknown").strip().upper()
    
    # Check for Insurance Details
    insurance_present = (inv.insurance_charges is not None and inv.insurance_charges > 0) or \
                        (inv.insurance_reference is not None and len(inv.insurance_reference) > 0) or \
                        (bol.insurance_reference is not None and len(bol.insurance_reference) > 0)
    
    status = "No"
    reason = "No insurance certificate is required based on current document context."
    confidence = "90%"
    
    if incoterm == "CIF":
        if not insurance_present:
            status = "Yes"
            reason = "Incoterm is CIF but no insurance details found in Invoice"
            confidence = "91%"
        else:
            status = "No"
            reason = "Incoterm is CIF and valid insurance details were detected in the documentation."
            confidence = "93%"
    elif incoterm in ["CFR", "CPT", "CIP"]:
        # CFR often requires separate insurance proof
        if not insurance_present:
            status = "Yes"
            reason = f"Incoterm is {incoterm} which typically excludes insurance; a separate certificate is required."
            confidence = "89%"
        else:
            status = "No"
            reason = f"Incoterm is {incoterm} and voluntary insurance details were found."
            confidence = "92%"
    elif incoterm in ["FOB", "EXW", "FCA"]:
        status = "Yes"
        reason = f"Incoterm is {incoterm} (Main Carriage risk with Buyer); direct insurance coverage proof is required."
        confidence = "87%"
    else:
        if not insurance_present:
            status = "Yes"
            reason = "Unable to determine Incoterm and no insurance details found; insurance certificate recommended."
            confidence = "75%"

    return AgentResult(
        insurance_required=status,
        reason=reason,
        confidence=confidence
    )

def detect_insurance_ai(invoice_text: str, pl_text: str, bol_text: str) -> AgentResult:
    """
    Uses OpenAI GPT-4o-mini to perform high-precision 'Document AI' analysis.
    """
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a specialized Insurance Requirement Detection AI (Agent 1).
    Your task is to analyze three document text blocks (Invoice, PL, BOL) and determine 
    if an Insurance Certificate is required based on Incoterms and missing documentation.

    REQUIRED JSON SCHEMA:
    {
        "Insurance Certificate Required": "Yes/No",
        "Reason": "Detailed human-readable explanation (e.g., 'Incoterm is CFR but no insurance found')",
        "Confidence": "XX%"
    }

    DECISION LOGIC (Maritime/Air Law):
    1. If Incoterm is CIF, insurance is MANDATORY. If not found, result is "Yes".
    2. If Incoterm is 100% missing, result is "Yes" (Cautionary).
    3. If Incoterm is CFR, CIP, or CPT, insurance is usually NOT included; result is "Yes" (Separate proof required).
    4. If Incoterm is FOB, EXW, or FCA, main carriage risk is with the Buyer; result is "Yes" (Proof required).
    5. ONLY return "No" if explicit insurance charges or reference numbers are detected.

    Return ONLY the raw JSON object. No markdown.
    """

    user_prompt = f"""
    INVOICE TEXT:
    {invoice_text}
    
    PACKING LIST TEXT:
    {pl_text}
    
    BILL OF LADING TEXT:
    {bol_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        content = response.choices[0].message.content
        data = json.loads(content)
        return AgentResult(**data)
    except:
        raise ValueError("Invalid JSON response from AI")
