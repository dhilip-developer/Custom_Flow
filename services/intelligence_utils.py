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
    Extracts the first valid JSON object from a string using regex.
    Handles conversational noise, markdown backticks, and trailing garbage.
    """
    if not text: return "{}"
    clean = text.strip()
    # Remove markdown backticks if present
    clean = re.sub(r"```json\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"```\s*", "", clean, flags=re.IGNORECASE)
    
    # Target the outermost { ... }
    match = re.search(r"(\{.*\})", clean, re.DOTALL)
    if match:
        return match.group(1)
    return clean

# Initialize API Clients
def get_secrets():
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets.json")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            return json.load(f)
    return {}

secrets = get_secrets()

# Configure Gemini (New SDK)
gemini_client = genai.Client(api_key=secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY")))
GEMINI_MODEL_NAME = "gemini-3-flash-preview" 

# OpenRouter Client
client_or = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
)

# Grok (xAI) Client
client_grok = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=secrets.get("GROK_API_KEY", os.getenv("GROK_API_KEY"))
)

# Hugging Face Client (Secondary)
client_hf = InferenceClient(
    token=secrets.get("HUGGINGFACE_API_KEY", os.getenv("HUGGINGFACE_API_KEY"))
)

async def generate_llm_content(prompt: str, system_prompt: str = None, model: str = None) -> str:
    """
    Utility wrapper for LLM Inference with high-fidelity document awareness.
    Priority: Direct Gemini -> OpenRouter -> Grok -> HF Hub
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    errors = []

    # --- PHASE 0: Direct Gemini (Highest Precision, Priority) ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[Intelligence] Attempting Direct Gemini (Attempt {attempt+1}/{max_retries})")
            # Use the already initialized gemini_client (genai.Client)
            contents = []
            if system_prompt: contents.append(system_prompt)
            contents.append(prompt)
            
            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=GEMINI_MODEL_NAME, 
                contents=contents
            )
            if response and response.text:
                return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = (attempt + 1) * 5
                print(f"[Intelligence] Gemini Quota Hit. Throttling {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"[Intelligence] Gemini direct failed: {e}")
                errors.append(f"Gemini: {str(e)}")
                break # Non-quota error, move to fallback

    # --- PHASE 1: Try OpenRouter (Failover) ---
    or_models = [
        "google/gemma-2-9b-it:free", # FREE - High availability
        "meta-llama/llama-3.1-8b-instruct:free", # FREE - Backup
        "microsoft/phi-3-mini-128k-instruct:free" # FREE - Ultralight
    ]
    for target_model in or_models:
        try:
            print(f"[Intelligence] Fallback: OpenRouter with {target_model}")
            response = await asyncio.to_thread(
                client_or.chat.completions.create,
                model=target_model,
                messages=messages,
                max_tokens=800, # Conservative token window
                temperature=0.1
            )
            if response and response.choices[0].message.content:
                return response.choices[0].message.content
        except Exception as e:
            print(f"[Intelligence] OpenRouter {target_model} failed: {e}")
            errors.append(f"OpenRouter({target_model}): {str(e)}")

    # --- PHASE 2: Try HF Hub (Last Resort) ---
    hf_models = [
        "HuggingFaceH4/zephyr-7b-beta",
        "mistralai/Mistral-7B-Instruct-v0.2"
    ]
    for target_model in hf_models:
        try:
            print(f"[Intelligence] Last Resort: HF Hub with {target_model}")
            response = await asyncio.to_thread(
                client_hf.chat_completion,
                messages=messages,
                model=target_model,
                max_tokens=800
            )
            if response and response.choices[0].message.content:
                return response.choices[0].message.content
        except Exception as e:
            print(f"[Intelligence] HF Hub {target_model} failed: {e}")
            errors.append(f"HF({target_model}): {str(e)}")

    return '{"documents": []}' # Prevent crash on total failure


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
        result_json = json.loads(content)
        return result_json

    except Exception as e:
        print(f"Error extracting data (async): {e}")
        return {"Agent 3 Error": f"Failed to extract logic: {str(e)}"}


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
    """
    if not documents: return []
    merged_map = {} 
    
    for doc in documents:
        data = doc.structured_data
        dtype = doc.document_type.lower()
        doc_id = str(data.get("invoice_number") or data.get("bl_number") or 
                     data.get("hss_ref_no") or data.get("pl_number") or "").strip().upper()
        
        key = (dtype, doc_id)
        if key not in merged_map:
            merged_map[key] = doc
            continue
            
        base = merged_map[key].structured_data
        for field, value in data.items():
            if value and not base.get(field):
                base[field] = value
            elif field == "items" and isinstance(value, list):
                # FUZZY DEDUPLICATION FOR ITEMS
                base_items = base.get("items", [])
                for new_item in value:
                    is_duplicate = False
                    for b_item in base_items:
                        # Check Quantity + Fuzzy Name
                        if (str(new_item.get("quantity")) == str(b_item.get("quantity")) and 
                            fuzzy_name_match(new_item.get("name"), b_item.get("name"))):
                            is_duplicate = True
                            # Keep the longer name (usually has more detail)
                            if len(str(new_item.get("name"))) > len(str(b_item.get("name"))):
                                b_item["name"] = new_item["name"]
                            break
                    if not is_duplicate:
                        base_items.append(new_item)
                base["items"] = base_items
    for doc in documents:
        data = doc.structured_data
        dtype = doc.document_type.lower()
        
        # CLEANUP: Remove any internal text fields that Gemini might have hallucinated
        # This prevents the "occupying the entire row" issue in UIs.
        for blacklisted in ["raw_text", "text", "chunk", "payload", "full_text"]:
            data.pop(blacklisted, None)
            
        doc_id = str(data.get("invoice_number") or data.get("bl_number") or 
                     data.get("hss_ref_no") or data.get("pl_number") or 
                     data.get("policy_number") or "").strip().upper()
        
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
                elif isinstance(value, dict) and isinstance(base.get(field), dict):
                    base[field].update({k: v for k, v in value.items() if v})
                elif len(str(value)) > len(str(base[field])):
                    base[field] = value
                    
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

async def extract_chunk_with_gemini(chunk: str, system_prompt: str) -> List[Dict[str, Any]]:
    """Calls the robust LLM provider chain with automatic failover and JSON parsing."""
    prompt = f"EXTRACT FROM THIS TEXT CHUNK:\n{chunk}"
    try:
        # Use the robust provider chain (OpenRouter/Grok/HF)
        raw_response = await generate_llm_content(prompt, system_prompt)
        
        # Robustly extract JSON from the LLM conversation
        json_text = robust_json_unwrap(raw_response)
        data = json.loads(json_text)
        
        docs = data.get("documents", [])
        print(f"[Intelligence] Extracted {len(docs)} docs from chunk ({len(chunk)} chars)")
        return docs
    except Exception as e:
        print(f"[Intelligence] Chunk extraction failed: {str(e)[:100]}")
        return []

async def extract_with_super_agent(text: str) -> SuperExtractionResponse:
    """
    Advanced Structured Extraction Engine (V1.0 Final).
    Strictly follows the User-Defined Flowchart-Aligned Protocol.
    """
    start_time = time.time()
    
    # 1. PRE-PROCESS
    clean_text = text
    try:
        unwrapped = re.sub(r'^\s*\(?\s*(\{.*?\})\s*\)?\s*$', r'\1', text, flags=re.DOTALL)
        if unwrapped != text:
            temp_data = json.loads(unwrapped)
            if "raw_text" in temp_data: clean_text = temp_data["raw_text"]
    except: pass

    # 2. ADAPTIVE CHUNKING
    chunks = split_text_into_logical_chunks(clean_text)
    print(f"[Intelligence] Started Advanced Extraction ({len(clean_text)} chars, {len(chunks)} chunks)")
    
    system_prompt = """
    You are an advanced structured data extraction engine.

    🚨 CRITICAL OBJECTIVE:
    Extract ALL documents and ALL important fields accurately. 
    If a value exists in the input text -> it MUST appear in output.

    ---
    ## STEP 1: DOCUMENT IDENTIFICATION
    Identify: invoice, bill_of_lading, packing_list, high_seas_sale_agreement, freight_certificate, insurance_certificate, certificate_of_origin.

    ---
    ## STEP 2: CLASSIFICATION RULES (STRICT)
    1. IF currency = USD AND BL number exists -> document_type = freight_certificate (NOT invoice)
    2. IF contains [BL number, vessel, ports] -> bill_of_lading
    3. IF contains [weights, packages, marks] -> packing_list
    4. IF contains [agreement reference, buyer/seller transfer] -> high_seas_sale_agreement

    ---
    ## STEP 3: EXTRACTION RULES
    - Combine fragmented data into ONE document object per identifier.
    - If same document appears multiple times → MERGE them.
    - DO NOT extract irrelevant data (addresses, phone numbers, legal text).

    ---
    ## STEP 4: REQUIRED FIELDS (MANDATORY IF PRESENT)
    - INVOICE: invoice_number, invoice_date, buyer_name, seller_name, total_amount, currency, gst_number, po_number, po_date, place_of_supply, place_of_delivery, hsn_codes, items: [{name, quantity, unit_price, total_price, batch, hsn_code}]
    - BILL OF LADING: bl_number, bl_date, shipper, consignee, vessel_name, voyage_no, port_of_loading, port_of_destination, container_number, seal_number, gross_weight, net_weight, package_count, freight_terms
    - PACKING LIST: pl_number, pl_date, total_packages, gross_weight, net_weight, marks_and_numbers, product_details, pallet_details
    - HIGH SEAS SALE AGREEMENT: hss_ref_no, agreement_date, buyer, seller, bl_number, vessel_name, port_of_loading, port_of_destination, foreign_invoice_number, foreign_invoice_date, foreign_invoice_amount, currency, incoterms, buyer_po_number, buyer_po_date
    - FREIGHT CERTIFICATE: bl_number, vessel_name, total_amount, currency (USD), description_of_goods

    ---
    ## STEP 5: DATA NORMALIZATION
    - Numbers: "3,032,800.00" → 3032800 (integer/float only)
    - Weights: "21,749.200 KG" → 21749.2 (remove units)
    
    OUTPUT FORMAT (STRICT JSON):
    {"documents": [{"document_type": "...", "structured_data": {...}}]}
    """
    
    # 2.5 SEQUENTIAL BATCH EXTRACTION (To avoid provider rate limits)
    chunk_results = []
    print(f"[Intelligence] Processing {len(chunks)} chunks sequentially for maximum stability...")
    for i, chunk in enumerate(chunks, 1):
        res = await extract_chunk_with_gemini(chunk, system_prompt)
        chunk_results.append(res)
        if i % 3 == 0: await asyncio.sleep(1.5) # Compliance Breather for 15 RPM limits

    # 3. NON-DESTRUCTIVE MERGE
    raw_extracted = []
    for results in chunk_results:
        for item in results:
            raw_extracted.append(SuperExtractionResult(
                document_type=item.get("document_type", "unknown"),
                structured_data=item.get("structured_data", {})
            ))
            
    final_docs = merge_extractions(raw_extracted)
    print(f"[Intelligence] Extraction Complete. {len(final_docs)} unique docs grouped. Time: {time.time()-start_time:.2f}s")
    
    return SuperExtractionResponse(documents=final_docs)


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
    Handles multiple key formats from Agent 2 (Legacy vs SuperAgent).
    """
    system_prompt = """
    You are a Senior Customs Document Auditor (Agent 3).
    TASK: Verify if the structured JSON data provided (from Agent 2) supports the CLAIMED document type.
    
    VERIFICATION RULES:
    1. KEY MAPPING: 
       - Recognize Legacy Keys: 'INVOICE NUMBER AND DATE', 'BILL NO.', 'SHIPPER NAME', 'TOTAL VALUE', 'GROSS WEIGHT', etc.
       - Recognize SuperAgent Keys: 'document_number', 'bl_number', 'invoice_number', 'buyer_name', 'total_amount', etc.
    
    2. INTEGRITY CHECK (Confidence 0-100):
       - 90-100: Mandatory fields (Numbers + Dates + Entities) are present and valid.
       - 60-89: Some fields present, but missing primary identifiers (e.g. no Invoice #).
       - 0-59: Data is sparse, garbage, or belongs to a different document type.

    3. DOCUMENT NAME:
       - Refine the claim into a professional title (e.g. 'Tax Invoice', 'Ocean Bill of Lading', 'Commercial Packing List').

    4. STATUS:
       - VERIFIED: High integrity match.
       - PARTIAL: Matches type but data is incomplete for customs filing.
       - FAILED: Data clearly contradicts the document type.
    
    RETURN JSON ONLY.
    """

    prompt = f"""
    AUDIT REQUEST:
    Claimed Type: {document_type}
    Input Data: {json.dumps(data, indent=2)}
    
    Output JSON format:
    {{
      "status": "VERIFIED | FAILED | PARTIAL",
      "confidence": <float_0_to_100>,
      "document_name": "<Refined Professional Title>",
      "details": "<Brief explanation of audit findings>",
      "fields_verified": <int_count_of_valid_fields>
    }}
    """

    try:
        content = await generate_llm_content(prompt, system_prompt)
        # Clean potential markdown backticks
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.replace("```json", "").replace("```", "").strip()
            
        result = json.loads(clean_content)
        return VerificationResponse(**result)

    except Exception as e:
        print(f"[Intelligence] Error in verification: {e}")
        return VerificationResponse(
            status="FAILED",
            confidence=0.0,
            document_name=document_type,
            details=f"Verification failed due to error: {str(e)}",
            fields_verified=0
        )
def run_rule_based_audit(payload: Dict[str, Any]) -> CustomsIntelligenceResponse:
    """
    Agent 3: High-Precision Deterministic Auditor.
    Implements Field Validation (70%) + Rule Validation (30%).
    """
    REQUIRED_FIELDS = {
        "invoice": ["document_number", "document_date", "buyer_name", "seller_name", "total_amount", "currency"],
        "high_seas_sale_agreement": ["document_number", "document_date", "buyer_name", "seller_name", "bl_number", "bl_date", "vessel_name"],
        "bill_of_lading": ["bl_number", "bl_date", "shipper", "consignee", "vessel_name", "port_of_loading", "port_of_discharge", "container_number", "gross_weight", "net_weight", "packages"],
        "certificate_of_origin": ["certificate_number", "exporter_name", "importer_name", "country_of_origin", "description_of_goods"],
        "packing_list": ["document_number", "document_date", "seller_name", "buyer_name", "gross_weight", "net_weight", "packages"]
    }

    raw_docs = payload.get("documents", [])
    processed_docs = []
    doc_confidences = []
    global_critical = []
    global_warnings = []
    
    # 1. Collect values for Cross-Document Validation
    cross_bl_map = {} # doc_type -> value
    cross_inv_map = {}
    cross_vessel_map = {}
    
    present_types = [doc.get("document_type", "").lower() for doc in raw_docs]
    freight_detected = False
    insurance_detected = False

    # 2. Per-Document Validation
    for doc in raw_docs:
        dtype = doc.get("document_type", "").lower()
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
                if float(str(data.get("total_amount", 0)).replace(",","")) > 0: rules_passed += 1
                else: doc_critical.append("Total amount must be greater than zero.")
            except: doc_critical.append("Invalid total amount format.")
            
        if dtype in ["bill_of_lading", "packing_list"]:
            rules_total += 1
            try:
                gw = float(str(data.get("gross_weight", 0)).replace(",",""))
                nw = float(str(data.get("net_weight", 0)).replace(",",""))
                if gw >= nw: rules_passed += 1
                else: doc_critical.append("Gross weight cannot be less than Net weight.")
            except: doc_warnings.append("Could not parse weights for logical comparison.")

        if dtype == "packing_list":
            rules_total += 1
            if int(data.get("packages", 0)) > 0: rules_passed += 1
            else: doc_critical.append("Packing list must specify at least 1 package.")

        rule_score = (rules_passed / rules_total * 30) if rules_total > 0 else 30 # Default to 30 if no rules
        
        # Total Doc Confidence
        conf_score = round(completion_score + rule_score)
        doc_confidences.append(conf_score)
        
        # Collect for Global
        if data.get("bl_number"): cross_bl_map[dtype] = str(data.get("bl_number"))
        if data.get("document_number") and dtype == "invoice": cross_inv_map[dtype] = str(data.get("document_number"))
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
        
        global_critical.extend(doc_critical)
        global_warnings.extend(doc_warnings)

        # STEP 4: DETECT FREIGHT/INSURANCE
        if str(data.get("currency", "")).upper() == "USD" and data.get("bl_number"): freight_detected = True
        if data.get("policy_number") or data.get("insured_amount") or data.get("insured_party"): insurance_detected = True

    # 3. Cross-Document Validation Logic
    cross_issues = []
    def check_consistency(val_map, label):
        unique_vals = set(val_map.values())
        if len(unique_vals) > 1:
            cross_issues.append(f"Mismatch in {label}: Found {len(unique_vals)} different values across {list(val_map.keys())}")
            global_critical.append(f"CRITICAL: {label} mismatch across documents.")

    check_consistency(cross_bl_map, "BL Number")
    check_consistency(cross_vessel_map, "Vessel Name")

    # 4. Global Validation Check
    MUST_HAVE = ["invoice", "bill_of_lading", "packing_list"]
    missing_docs = [m for m in MUST_HAVE if m not in present_types]
    if missing_docs:
        global_critical.append(f"CRITICAL: Missing required documents: {', '.join(missing_docs)}")

    if not freight_detected and "freight_certificate" not in present_types:
        missing_docs.append("freight_certificate")
    if not insurance_detected and "insurance_certificate" not in present_types:
        missing_docs.append("insurance_certificate")

    # 5. Global Confidence & Penalties
    avg_conf = sum(doc_confidences) / len(doc_confidences) if doc_confidences else 0
    overall_conf = round(avg_conf)
    
    if global_critical: overall_conf -= 20
    elif global_warnings: overall_conf -= 10
    
    overall_conf = max(0, min(100, overall_conf))

    # 6. Final Clearance Decision
    # Ready ONLY IF mandatory docs present AND zero critical issues
    has_mandatory = all(m in present_types for m in MUST_HAVE)
    clearance_ready = has_mandatory and len(global_critical) == 0

    return CustomsIntelligenceResponse(
        documents=processed_docs,
        global_validation=GlobalValidationResult(
            missing_documents=missing_docs,
            cross_document_issues=cross_issues,
            critical_issues=list(set(global_critical)),
            warnings=list(set(global_warnings)),
            overall_confidence=overall_conf,
            clearance_ready=clearance_ready
        )
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
            documents=[],
            global_validation=GlobalValidationResult(
                missing_documents=[],
                cross_document_issues=[f"Rule Engine Error: {str(e)}"],
                overall_confidence=0,
                clearance_ready=False
            )
        )
