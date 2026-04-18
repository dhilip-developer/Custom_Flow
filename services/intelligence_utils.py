import time
import json
import asyncio
import os
import re
from typing import List, Dict, Any, Optional
from google import genai
from huggingface_hub import InferenceClient
from openai import OpenAI
from models.schemas import (
    ClassificationResponse, DocumentType, FreightCertificateCheckResponse,
    CleanedDocumentResponse,
    SuperExtractionResponse, SuperExtractionResult,
    VerificationResponse, CustomsIntelligenceResponse, CustomsAuditRequest,
    CustomsIntelligenceResult, GlobalValidationResult
)

def robust_json_unwrap(text: str) -> str:
    """
    Extracts the largest valid JSON block from a string.
    (Step 4: JSON Hardening).
    """
    if not text: return "{}"
    clean = text.strip()
    # Remove markdown backticks if present
    clean = re.sub(r"```json\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"```\s*", "", clean, flags=re.IGNORECASE)
    
    # Priority: Greedy match for outermost { ... } to handle conversational prefixes
    match = re.search(r"(\{[\s\S]*\})", clean)
    if match:
        return match.group(1)
    return clean

def sanitize_json(text: str) -> str:
    """
    Fix common LLM JSON malformations before json.loads().
    (Step 4: JSON Hardening - Fix missing commas).
    """
    if not text: return text
    
    # 1. Fix missing commas between key-value pairs
    # Pattern: "key": "value" "next_key":
    text = re.sub(r'("[\w_]+":\s*(?:"[^"]*"|\d+(?:\.\d+)?|true|false|null))\s*("[\w_]+":)', r'\1,\2', text)
    
    # 2. Fix missing commas between elements in a list
    # Pattern: } { or ] [
    text = re.sub(r'\}\s*\{', '},{', text)
    text = re.sub(r'\]\s*\[', '],[', text)
    
    # 3. Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    
    return text

# Initialize API Clients
def get_secrets():
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets.json")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            return json.load(f)
    return {}

secrets = get_secrets()

# Configure OpenAI (ChatGPT) 
openai_client = OpenAI(
    api_key=secrets.get("OPENAI_API_KEY", "")
)

async def generate_llm_content(prompt: str, system_prompt: str = None, model: str = None) -> str:
    """
    Utility wrapper for LLM Inference using OpenAI ChatGPT.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            print(f"[Intelligence] Attempting OpenAI ChatGPT (gpt-4o-mini) - Attempt {attempt+1}/{max_retries}")
            response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=4096,
                temperature=0.0
            )
            if response and response.choices:
                return response.choices[0].message.content
            return "{}"
        except Exception as e:
            last_error = str(e)
            print(f"[Intelligence] OpenAI ChatGPT Error: {e}")
            if "429" in last_error or "503" in last_error:
                wait_time = 2 ** attempt
                print(f"[Intelligence] Rate limited. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                break
                
    print(f"[Intelligence] CRITICAL: OpenAI ChatGPT failed after retries: {last_error}")
    raise Exception(f"OpenAI ChatGPT FAILED: {last_error}")


def generate_gemini_content_with_retry(client, model, contents, config, max_retries=5):
    """
    BACKWARD COMPATIBILITY WRAPPER.
    Redirects old Agent 1/2/4/5 calls to the new OpenRouter backend.
    """
    # contents is usually [system_prompt, user_prompt] or just [user_prompt]
    if len(contents) > 1:
        sys_p = str(contents[0])
        usr_p = str(contents[1])
    else:
        sys_p = None
        usr_p = str(contents[0])

    try:
        content = asyncio.run(generate_llm_content(usr_p, sys_p))
    except RuntimeError:
        # Loop already running (Uvicorn environment)
        import nest_asyncio
        nest_asyncio.apply()
        content = asyncio.run(generate_llm_content(usr_p, sys_p))
    
    # Mock a response object that has a .text property
    class MockResponse:
        def __init__(self, text):
            self.text = text
    
    return MockResponse(content)


async def classify_document_async(text: str) -> List[ClassificationResponse]:
    """Agent 2: Specialized document-level classification using Mixtral."""
    system_prompt = """
    You are a document classifier.
    Input: Text from one document chunk.
    Task: Identify the document type.
    
    Choose ONE from:
    - invoice
    - annexure
    - agreement
    - bill_of_lading
    - freight_certificate
    - insurance_certificate

    Rules:
    - If text contains "Invoice No" -> invoice
    - If text contains "Annexure" -> annexure
    - If text contains "HIGH SEAS SALE AGREEMENT" -> agreement
    - If text contains "B/L Number" -> bill_of_lading
    - If text contains shipping/logistics company -> freight_certificate
    - If text contains "Insurance" or "Policy" -> insurance_certificate

    Output JSON:
    {
      "document_type": "...",
      "confidence": 0.95
    }
    No explanation.
    """
    
    prompt = f"TEXT TO CLASSIFY:\n{text[:5000]}"

    try:
        content = await generate_llm_content(prompt, system_prompt)
        # Clean potential markdown backticks
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(clean_content)
            
        # Map results to standard types
        raw_type = data.get("document_type", "unknown").lower()
        conf = data.get("confidence", 0.0)

        # Standard Mapping Table (Mixtral lowercase -> System Title Case)
        TYPE_MAP = {
            "invoice": "Invoice",
            "bill_of_lading": "Bill of Lading (BOL)",
            "packing_list": "Packing List",
            "agreement": "High Sea Sale Agreement (HSS)",
            "high_seas_sale_agreement": "High Sea Sale Agreement (HSS)",
            "annexure": "Additional Documents",
            "freight_certificate": "Freight Certificate",
            "insurance_certificate": "Insurance Certificate",
            "coo": "Certificate of Origin",
            "certificate_of_origin": "Certificate of Origin",
        }

        doc_type = TYPE_MAP.get(raw_type, raw_type)

        # HEURISTIC RECOVERY: If AI says unknown, but we see strong keywords
        if doc_type.lower() in ("unknown", "skipped", "error"):
            text_lower = text.lower()
            if "invoice" in text_lower or "bill of" in text_lower or "tax" in text_lower:
                doc_type = "Invoice"
            elif "lading" in text_lower or "b/l" in text_lower or "bol" in text_lower:
                doc_type = "Bill of Lading (BOL)"
            elif "annexure" in text_lower or "appendix" in text_lower:
                doc_type = "Additional Documents"

        return [ClassificationResponse(document_type=doc_type, confidence=conf)]

    except Exception as e:
        print(f"[Intelligence] Error in standalone classification: {e}")
        return [ClassificationResponse(document_type="unknown", confidence=0.0)]


def classify_document(text: str) -> List[ClassificationResponse]:
    """Sync wrapper for Agent 2."""
    try:
        return asyncio.run(classify_document_async(text))
    except:
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(classify_document_async(text))


async def clean_and_structure_text(type_hint: str, content: str) -> CleanedDocumentResponse:
    """
    Preprocessing tool: Cleans raw OCR text and structures it according to the provided prompt.
    """
    system_prompt = """
    You are a document cleaning and light structuring assistant.
    You will receive OCR extracted text from a document page or group of pages.
    The document may contain: Invoice, Agreement, Annexure, Certificate, Letter, Mixed content.

    Your goal is NOT to fully extract all data.
    Your goal is to CLEAN the text, REMOVE noise, and RETURN a structured output.

    TASKS:
    STEP 1: CLEAN THE TEXT
    - Remove duplicate repeated lines or blocks
    - Remove headers and footers like: "Page X of Y", "Authorised Signatory", "For Company Name", "INTERNAL"
    - Fix obvious OCR mistakes (e.g. "Wrist Weight" -> "Gross Weight")
    - Fix broken words and spacing if clearly wrong
    - Keep all important business content

    STEP 2: DO NOT REMOVE IMPORTANT DATA
    - Do NOT delete: Invoice details, Product details, Amounts, Dates, Names and addresses, Table-like data.
    - If unsure, KEEP the content.

    STEP 3: KEEP TEXT COMPACT
    - Merge broken lines into readable sentences.
    - Remove unnecessary line breaks.
    - Keep content clear and readable.

    STEP 4: OUTPUT FORMAT (STRICT)
    Return ONLY valid JSON.
    {
      "type": "<type_hint>",
      "cleaned_text": "<cleaned and readable text>"
    }

    RULES:
    - Do NOT explain anything
    - Do NOT add extra fields
    - Do NOT return raw OCR
    - Do NOT summarize content
    - Do NOT hallucinate values
    - Keep output small and clean
    """

    try:
        raw_response = await generate_llm_content(f"INPUT:\ntype_hint: {type_hint}\ncontent: {content}", system_prompt)
        print(f"[Intelligence] Cleaned Text (Preview): {raw_response[:100]}...")
        data = json.loads(raw_response)
        return CleanedDocumentResponse(**data)

    except Exception as e:
        print(f"[Intelligence] Error in document cleaning: {e}")
        return CleanedDocumentResponse(
            type=type_hint,
            cleaned_text=content # Fallback to raw content
        )




async def extract_data_from_text_async(document_type: str, text: str) -> dict:
    """Async version of Agent 2 extraction for parallel processing."""
    system_prompt = f"""
    You are a highly accurate document data extractor.
    The document you are analyzing is classified as: '{document_type}'.

    TASK:
    Extract structured data for this '{document_type}' from the provided text.
    - Extract ALL fields belonging to this document type.
    - DO NOT skip values if present anywhere in text.
    - SEARCH ENTIRE TEXT before marking a field missing.

    CRITICAL EXTRACTION RULES:
    ✅ ALWAYS EXTRACT (HIGH PRIORITY):
    - document_number / invoice_number, document_date
    - buyer_name, seller_name, total_amount, currency, gst_number
    - po_number, po_date, bl_number, bl_date, vessel_name
    - port_of_loading, port_of_destination, gross_weight, net_weight
    - packages / quantity
    - product_details (name, qty, unit, price, batch, hsn_code)

    ❌ STRICTLY IGNORE:
    - full addresses, terms & conditions, legal text, signatures, repeated company footers.

    IMPORTANT LOGIC:
    1. NEVER RETURN EMPTY JSON. If data exists, you MUST extract it.
    2. HANDLE OCR NOISE. Even if text is broken or misaligned, extract values.
    3. DO NOT GUESS. Only extract values present in text.

    Return the response ONLY as a flat JSON dictionary:
    {{
       "KEY_NAME": "EXTRACTED_VALUE",
       ...
    }}
    """

    try:
        content = await generate_llm_content(f"DOCUMENT RAW TEXT PAYLOAD:\n{text}", system_prompt)
        # Sanitize LLM response before parsing
        clean_content = robust_json_unwrap(content)
        clean_content = sanitize_json(clean_content)
        result_json = json.loads(clean_content)
        return result_json

    except Exception as e:
        print(f"[Agent 2] Error extracting data (async): {e}")
        return {"Agent 2 Error": f"Failed to extract logic: {str(e)}"}


def extract_data_from_text(document_type: str, text: str) -> dict:
    """Sync wrapper for Agent 3 extraction (for legacy support)."""
    try:
        return asyncio.run(extract_data_from_text_async(document_type, text))
    except Exception as e:
        # If already in an event loop, we need a different approach
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(extract_data_from_text_async(document_type, text))


async def extract_data_batch(smart_extraction_results: Any) -> List[dict]:
    """
    Agent 3 Batch Mode: Processes multiple extracted documents in parallel.
    Uses 'cleaned_text' from Agent 1's preprocessing for better accuracy.
    """
    tasks = []
    metadata = []

    # 'smart_extraction_results' is expected to be a SmartExtractionResponse object or dict
    if hasattr(smart_extraction_results, 'documents'):
        documents = smart_extraction_results.documents
    else:
        documents = smart_extraction_results.get('documents', [])

    for doc in documents:
        if hasattr(doc, 'text'):
            # Prefer cleaned_text if available, fallback to raw text
            text_to_use = getattr(doc, 'cleaned_text', doc.text)
            doc_type = doc.document_type
            page_range = doc.page_range
        else:
            text_to_use = doc.get('cleaned_text', doc.get('text', ''))
            doc_type = doc.get('document_type', 'unknown')
            page_range = doc.get('page_range', 'unknown')

        tasks.append(extract_data_from_text_async(doc_type, text_to_use))
        metadata.append({
            "page_range": page_range,
            "document_type": doc_type
        })

    if not tasks:
        return []

    # Run all extractions in parallel
    results = await asyncio.gather(*tasks)

    # Combine results with metadata
    batch_results = []
    for i, res in enumerate(results):
        # res can sometimes be a string from HF, parse if needed
        if isinstance(res, str):
            try:
                # Clean markdown backticks if present
                clean_res = res.strip()
                if clean_res.startswith("```json"):
                    clean_res = clean_res.replace("```json", "").replace("```", "").strip()
                res = json.loads(clean_res)
            except:
                res = {"raw_output": res}

        batch_results.append({
            "page_range": metadata[i]["page_range"],
            "document_type": metadata[i]["document_type"],
            "extracted_data": res
        })

    return batch_results

def fuzzy_name_match(name1: str, name2: str) -> bool:
    """True if names are significantly similar (e.g., handles batch/code noise)."""
    n1, n2 = str(name1).lower(), str(name2).lower()
    if n1 == n2: return True
    # If one is a substring of the other and they share first 10 chars
    if (n1 in n2 or n2 in n1) and n1[:10] == n2[:10]:
        return True
    return False

def split_text_into_logical_chunks(text: str, chunk_size: int = 8000, overlap: int = 1000) -> List[str]:
    """
    Adaptive splitter that combines page-based detection with sliding windows.
    """
    # Expanded regex for complex headers like "1/3 Original for Recipient..."
    page_markers = [
        r"\d+/\d+\s+Original", 
        r"Page:\s+\d+/\d+", 
        r"Invoice\s+No\.:\s+\w+",
        r"SEA\s+WAYBILL",
        r"HSS\s+Agreement\s+Ref"
    ]
    combined_pattern = "|".join(page_markers)
    
    matches = list(re.finditer(combined_pattern, text, re.IGNORECASE))
    
    if len(matches) > 1:
        chunks = []
        last_pos = 0
        for m in matches:
            if m.start() - last_pos > 800: # Threshold for logical document size
                chunks.append(text[last_pos:m.start()].strip())
                last_pos = m.start()
        chunks.append(text[last_pos:].strip())
        print(f"[Intelligence] Adaptive Splitter: Used {len(matches)} markers")
        return [c for c in chunks if len(c) > 50]

    # Fallback to Sliding Window
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]

def merge_extractions(documents: List[SuperExtractionResult]) -> List[SuperExtractionResult]:
    """
    Intelligently merges partial extractions with fuzzy deduplication for items.
    Handles orphan docs (no identifier) by attaching them to same-type docs.
    """
    if not documents: return []
    
    merged_map = {}
    last_id_for_type = {}
    orphans = []
    
    for doc in documents:
        data = doc.structured_data
        dtype = doc.document_type.lower()
        
        # CLEANUP: Remove any internal text fields that Gemini might have hallucinated
        for blacklisted in ["raw_text", "text", "chunk", "payload", "full_text"]:
            data.pop(blacklisted, None)
            
        doc_id = str(
            data.get("invoice_number") or data.get("bl_number") or 
            data.get("hss_ref_no") or data.get("pl_number") or 
            data.get("policy_number") or ""
        ).strip().upper()
        
        # Inherit ID from previous doc of same type if this one has none
        if not doc_id and dtype in last_id_for_type:
            doc_id = last_id_for_type[dtype]
            
        if not doc_id:
            orphans.append(doc)
            continue
            
        last_id_for_type[dtype] = doc_id
        key = (dtype, doc_id)
        
        if key not in merged_map:
            merged_map[key] = doc
        else:
            base = merged_map[key].structured_data
            for field, value in data.items():
                if not value: continue
                if not base.get(field):
                    base[field] = value
                elif field == "items" and isinstance(value, list):
                    # FUZZY DEDUPLICATION FOR ITEMS
                    base_items = base.get("items", [])
                    for new_item in value:
                        is_dup = False
                        for b_item in base_items:
                            if (str(new_item.get("quantity")) == str(b_item.get("quantity")) and 
                                fuzzy_name_match(new_item.get("name"), b_item.get("name"))):
                                is_dup = True
                                if len(str(new_item.get("name"))) > len(str(b_item.get("name"))):
                                    b_item["name"] = new_item["name"]
                                break
                        if not is_dup: base_items.append(new_item)
                    base["items"] = base_items
                elif isinstance(value, dict) and isinstance(base.get(field), dict):
                    base[field].update({k: v for k, v in value.items() if v})
                elif len(str(value)) > len(str(base[field])):
                    base[field] = value
                    
    # Attach orphan docs to same-type merged docs, or keep as standalone
    final_docs = list(merged_map.values())
    for orphan in orphans:
        matches = [d for d in final_docs if d.document_type.lower() == orphan.document_type.lower()]
        if matches:
            base = matches[0].structured_data
            for f, v in orphan.structured_data.items():
                if v and not base.get(f) and f not in ["raw_text", "text"]: 
                    base[f] = v
        else:
            final_docs.append(orphan)
            
    return final_docs

async def extract_chunk_with_gemini(raw_text: str, document_type: str = "unknown") -> List[Dict[str, Any]]:
    """
    Step 3: Core Extraction Engine (14 Core Rules Alignment).
    Identifies and extracts structured data from OCR text with strict validation.
    """
    system_prompt = """
    You are an intelligent document understanding system specialized in logistics and customs documents.

    Your task is to convert RAW OCR TEXT into STRICT STRUCTURED JSON.

    ---

    ## 🔹 CRITICAL INSTRUCTIONS

    1. DOCUMENT UNDERSTANDING FIRST (MANDATORY)
    * Identify the PRIMARY document type:
      * "invoice"
      * "packing_list"
      * "bill_of_lading"
      * "freight_certificate"
      * "insurance_certificate"
      * "unknown"

    ---

    ## 🔹 MANDATORY FIELDS PER DOCUMENT TYPE
    Extract the following fields STRIYLY for each type:

    ### 1. Invoice
    - invoice_number, invoice_date
    - shipper_name_address, consignee_name_address
    - po_number, po_item, incoterms
    - amount, currency, gst_number
    - part_no, description, country_of_origin
    - qty_units, unit_price, net_value, gross_value
    - hsn_codes

    ### 2. Bill of Lading (BOL)
    - bl_number, bl_date
    - shipper, consignee, forwarder, notify_party
    - vessel_name, voyage_no, port_of_loading, port_of_destination
    - container_number, container_type, seal_number
    - gross_weight, net_weight, package_count
    - freight_terms, description_of_goods, measurement

    ### 3. Packing List
    - invoice_number, invoice_date
    - shipper, consignee, po_number
    - gross_weight, net_weight
    - marks_and_numbers, qty, pallet_details
    - part_number, country_of_origin, hs_code, description

    ### 4. Freight Certificate
    - bl_number, freight_charges, currency
    - weight (including c.wt), incoterms, packages
    - pol, pod, consignee
    - excharge_charges, container_type, date

    ### 5. Insurance Certificate
    - policy_number, issue_date, gst_uin_number
    - invoice_number, invoice_date
    - address, description, po_number
    - insured_amount, currency
    - pod, pol, exchange_rate, description_of_goods

    ---

    ## 🔹 EXTRACTION RULES
    * Treat entire input as ONE document.
    * Use semantic understanding, not exact keywords.
    * Convert amounts/weights to float (remove commas).
    * Convert dates to YYYY-MM-DD.
    * If missing -> set to null.

    ---

    ## 🔹 STRICT OUTPUT FORMAT (MANDATORY)
    Return ONLY ONE JSON object:

    {
      "document_type": "<DETECTED_TYPE>",
      "structured_data": {
        "FIELD_NAME": "VALUE",
        ...
      },
      "items": [],
      "confidence_score": 95,
      "missing_fields": []
    }
    """
    prompt = f"EXTRACT FROM THIS RAW OCR TEXT:\n{raw_text}"
    
    try:
        raw_response = await generate_llm_content(prompt, system_prompt)
        json_text = robust_json_unwrap(raw_response)
        json_text = sanitize_json(json_text)
        data = json.loads(json_text)
        
        docs = data.get("documents", [])
        if not docs and isinstance(data, dict) and "structured_data" in data:
            docs = [data]
            
        for d in docs:
            if "document_type" not in d or d["document_type"] == "unknown":
                d["document_type"] = document_type
            
        return docs
    except Exception as e:
        print(f"[Intelligence] CRITICAL: LLM Extraction Failed for {document_type}: {e}")
        return [{
            "document_type": document_type,
            "structured_data": {},
            "items": []
        }]

async def extract_with_super_agent(text: str) -> SuperExtractionResponse:
    """
    Agent 2: Phase 2 Modular Pipeline Entry Point.
    Wires the router directly to the Hybrid Extraction Engine.
    (Fix 1, 3: Force Pipeline and Hybrid Engine usage).
    """
    from services.extraction_engine.hybrid_engine import extract_with_hybrid_engine
    
    print(f"[Agent 2] Gemini Super Engine Activation ({len(text)} chars)")
    
    # Trigger the Modular Hybrid Engine (Segmentation -> Gemini -> Validate -> Merge)
    result = await extract_with_hybrid_engine(text)
    
    # Step 9: Return matched to schema including diagnostic flags
    return SuperExtractionResponse(
        documents=result["documents"],
        extraction_mode=result.get("extraction_mode", "gemini"),
        llm_failed=result.get("llm_failed", False),
        error=result.get("error")
    )


async def detect_freight_certificate_requirement_async(text: str) -> FreightCertificateCheckResponse:
    """Agent 4: Analyses raw plain text to determine if a Freight Certificate is required."""
    if not text or not text.strip():
        return FreightCertificateCheckResponse(
            freight_certificate_required="needed",
            status_label="Required",
            reason="No document text was supplied. Defaulting to Required.",
            confidence=95.0
        )

    system_prompt = """
    You are a document detector.
    Input: Structured data from documents.
    Task: Check if the following exist:
    - freight details
    - insurance details

    Rules:
    - If B/L Number or vessel exists -> freight = true
    - If policy number or insurance words exist -> insurance = true

    Output JSON:
    {
      "freight_present": true/false,
      "insurance_present": true/false
    }
    No explanation.
    """
    try:
        content = await generate_llm_content(f"DATA TO CHECK:\n{text.strip()}", system_prompt)
        # Clean markdown
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(clean_content)
        
        # Map to expected response
        is_needed = "needed" if result.get("freight_present") else "not needed"
        label = "Required" if result.get("freight_present") else "Not Required"
        
        return FreightCertificateCheckResponse(
            freight_certificate_required=is_needed,
            status_label=label,
            reason="Based on logistics field detection",
            confidence=0.95
        )
    except Exception as e:
        print(f"Error in Agent 4: {e}")
        return FreightCertificateCheckResponse(
            freight_certificate_required="needed",
            status_label="Required",
            reason=f"Error: {e}",
            confidence=0.0
        )


def detect_freight_certificate_requirement(text: str) -> FreightCertificateCheckResponse:
    """Sync wrapper for Agent 4."""
    try:
        return asyncio.run(detect_freight_certificate_requirement_async(text))
    except:
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(detect_freight_certificate_requirement_async(text))

async def verify_extracted_data_async(document_type: str, data: Dict[str, Any]) -> VerificationResponse:
    """
    Agent 3: Verifies if the extracted data supports the classified document type.
    Uses strict deterministic rule-based checking for maximum speed and accuracy.
    """
    REQUIRED_FIELDS = {
        "invoice": [
            "invoice_number", "invoice_date", "shipper_name_address", "consignee_name_address", 
            "po_number", "amount", "currency", "part_no", "description", "qty_units"
        ],
        "bill_of_lading": [
            "bl_number", "bl_date", "shipper", "consignee", "vessel_name", 
            "port_of_loading", "port_of_destination", "container_number"
        ],
        "packing_list": [
            "invoice_number", "invoice_date", "shipper", "consignee", 
            "gross_weight", "net_weight"
        ],
        "freight_certificate": [
            "bl_number", "freight_charges", "currency", "weight", "pol", "pod"
        ],
        "insurance_certificate": [
            "policy_number", "issue_date", "invoice_number", "insured_amount", "currency"
        ]
    }
    
    # Normalize document type
    dtype = document_type.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
    # Fuzzy match
    if "invoice" in dtype: dtype = "invoice"
    elif "lading" in dtype or "bol" in dtype: dtype = "bill_of_lading"
    elif "packing" in dtype: dtype = "packing_list"
    elif "freight" in dtype: dtype = "freight_certificate"
    elif "insurance" in dtype: dtype = "insurance_certificate"
    elif "origin" in dtype: dtype = "certificate_of_origin"
    elif "high_seas" in dtype or "hss" in dtype or "agreement" in dtype: dtype = "high_seas_sale_agreement"

    required = REQUIRED_FIELDS.get(dtype, [])
    
    if not required:
        return VerificationResponse(
            status="PARTIAL",
            confidence=50.0,
            document_name=document_type,
            details="Unknown document type or no mandatory fields defined for verification.",
            fields_verified=0,
            missing_fields=[]
        )

    found_fields = []
    missing_fields = []

    for field in required:
        val = data.get(field)
        if val and str(val).strip() and str(val).lower() != "n/a":
            found_fields.append(field)
        else:
            missing_fields.append(field)

    total_fields = len(required)
    confidence = (len(found_fields) / total_fields) * 100.0 if total_fields > 0 else 0.0

    status = "VERIFIED" if confidence > 80.0 else "PARTIAL"
    
    details = f"Found {len(found_fields)}/{total_fields} mandatory fields."
    if missing_fields:
        details += f" Missing critical values."
        
    return VerificationResponse(
        status=status,
        confidence=round(confidence, 2),
        document_name=document_type,
        details=details,
        fields_verified=len(found_fields),
        missing_fields=missing_fields
    )
def run_rule_based_audit(payload: Dict[str, Any]) -> CustomsIntelligenceResponse:
    """
    Agent 3: High-Precision Deterministic Auditor.
    Implements Field Validation (70%) + Rule Validation (30%).
    """
    # 1. Configuration - Required Fields per Document Type (User Mandatory List)
    REQUIRED_FIELDS = {
        "invoice": [
            "invoice_number", "invoice_date", "shipper_name_address", "consignee_name_address", 
            "po_number", "amount", "currency", "part_no", "description", "qty_units"
        ],
        "bill_of_lading": [
            "bl_number", "bl_date", "shipper", "consignee", "vessel_name", 
            "port_of_loading", "port_of_destination", "container_number"
        ],
        "packing_list": [
            "invoice_number", "invoice_date", "shipper", "consignee", 
            "gross_weight", "net_weight"
        ],
        "freight_certificate": [
            "bl_number", "freight_charges", "currency", "weight", "pol", "pod"
        ],
        "insurance_certificate": [
            "policy_number", "issue_date", "invoice_number", "insured_amount", "currency"
        ]
    }

    raw_docs = payload.get("documents", [])
    processed_docs = []
    doc_confidences = []
    
    # Cross-verification maps
    cross_bl_map = {}
    cross_inv_map = {}
    cross_vessel_map = {}

    # 2. Per-Document Validation
    for doc in raw_docs:
        dtype_raw = doc.get("document_type", "").lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
        
        # Fuzzy match
        dtype = dtype_raw
        if "invoice" in dtype: dtype = "invoice"
        elif "lading" in dtype or "bol" in dtype: dtype = "bill_of_lading"
        elif "packing" in dtype: dtype = "packing_list"
        elif "freight" in dtype: dtype = "freight_certificate"
        elif "insurance" in dtype: dtype = "insurance_certificate"
        elif "origin" in dtype: dtype = "certificate_of_origin"
        elif "high_seas" in dtype or "hss" in dtype or "agreement" in dtype: dtype = "high_seas_sale_agreement"
        
        data = doc.get("structured_data", {})
        doc_critical = []
        doc_warnings = []
        
        # --- SUB-STEP A: Field Completion (70%) ---
        required = REQUIRED_FIELDS.get(dtype, [])
        total_fields = len(required)
        found_fields = []
        missing_fields = []
        
        for field in required:
            val = data.get(field)
            if val and str(val).strip() and str(val).lower() != "n/a":
                found_fields.append(field)
            else:
                missing_fields.append(field)
        
        completion_score = (len(found_fields) / total_fields * 70) if total_fields > 0 else 0
        
        # --- SUB-STEP B: Rule Validation Pass (30%) ---
        rules_total = 0
        rules_passed = 0
        
        # Define rules
        if dtype == "invoice":
            rules_total += 1
            try:
                amt_val = data.get("amount") or data.get("total_amount")
                if float(str(amt_val or 0).replace(",","")) > 0: rules_passed += 1
                else: doc_critical.append("Invoice amount must be greater than zero.")
            except: doc_critical.append("Invalid amount format.")
            
        if dtype in ["bill_of_lading", "packing_list"]:
            rules_total += 1
            try:
                gw = float(str(data.get("gross_weight", 0)).replace(",",""))
                nw = float(str(data.get("net_weight", 0)).replace(",",""))
                if gw >= nw: rules_passed += 1
                else: doc_critical.append("Gross weight cannot be less than Net weight.")
            except: doc_warnings.append("Could not parse weights for logical comparison.")

        rule_score = (rules_passed / rules_total * 30) if rules_total > 0 else 30 
        
        # Total Doc Confidence
        conf_score = round(completion_score + rule_score)
        doc_confidences.append(conf_score)
        
        # Collect for Global
        if data.get("bl_number"): cross_bl_map[dtype] = str(data.get("bl_number"))
        if data.get("invoice_number"): cross_inv_map[dtype] = str(data.get("invoice_number"))
        if data.get("vessel_name"): cross_vessel_map[dtype] = str(data.get("vessel_name"))

        processed_docs.append(CustomsIntelligenceResult(
            document_type=dtype,
            total_fields=total_fields,
            found_fields=len(found_fields),
            missing_fields=missing_fields,
            confidence_score=conf_score,
            warnings=doc_warnings,
            critical_issues=doc_critical
        ))

    return CustomsIntelligenceResponse(
        documents=processed_docs
    )

async def run_customs_intelligence_async(payload: Dict[str, Any]) -> CustomsIntelligenceResponse:
    """
    Agent 3: Customs Intelligence Engine.
    Now optimized with Rule-Based Logic for $0 cost and instant response.
    """
    try:
        print("[Intelligence] Executing Rule-Based Audit Engine...")
        return run_rule_based_audit(payload)
    except Exception as e:
        print(f"[Intelligence] Error in Rule Engine: {e}")
        return CustomsIntelligenceResponse(
            documents=[]
        )
