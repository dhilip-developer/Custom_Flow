"""
Agent 1: Document Processor — Simplified Raw Text Extraction Pipeline.

Architecture:
    PDF → PyMuPDF digital text check → if text exists, return immediately
                                     → if scanned, send to Document AI OCR
    
    Agent 2's regex engine handles splitting, classification, and extraction.
    Agent 1 only needs to produce raw text. No LLM calls. No thumbnails.
"""
import io
import time
import fitz  # PyMuPDF
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from models.schemas import SmartExtractionResponse

# Lazy-loaded Document AI client (only if scanned PDFs detected)
_docai_client = None
_docai_executor = ThreadPoolExecutor(max_workers=4)


def _get_docai_client():
    """Initialize Document AI client on first use only."""
    global _docai_client
    if _docai_client is None:
        try:
            import os
            from google.cloud import documentai
            from shared.config import load_credentials, DOCAI_CONFIG, PROJECT_ROOT

            load_credentials()
            creds_path = os.path.join(PROJECT_ROOT, DOCAI_CONFIG["credentials_file"])
            _docai_client = {
                "client": documentai.DocumentProcessorServiceClient.from_service_account_file(creds_path),
                "processor_name": (
                    f"projects/{DOCAI_CONFIG['project_id']}"
                    f"/locations/{DOCAI_CONFIG['location']}"
                    f"/processors/{DOCAI_CONFIG['processor_id']}"
                ),
                "documentai": documentai,
            }
            print("[Agent1] Document AI client initialized (for scanned PDFs)")
        except Exception as e:
            print(f"[Agent1] WARNING: Document AI unavailable: {e}")
            print("[Agent1] Scanned PDFs will use PyMuPDF fallback (lower quality)")
            _docai_client = {"error": str(e)}
    return _docai_client


def _ensure_pdf(file_bytes: bytes) -> bytes:
    """Convert Word docs to PDF if needed. Pass-through for PDFs."""
    if not file_bytes:
        return file_bytes

    if file_bytes.startswith(b"%PDF-"):
        return file_bytes

    is_docx = file_bytes.startswith(b"PK\x03\x04")
    is_doc = file_bytes.startswith(b"\xd0\xcf\x11\xe0")

    if is_docx or is_doc:
        try:
            import aspose.words as aw
            doc_stream = io.BytesIO(file_bytes)
            doc = aw.Document(doc_stream)
            pdf_stream = io.BytesIO()
            doc.save(pdf_stream, aw.SaveFormat.PDF)
            print(f"[Agent1] Converted Word doc to PDF")
            return pdf_stream.getvalue()
        except ImportError:
            print("[Agent1] WARNING: aspose-words not installed, cannot convert Word docs")
        except Exception as e:
            print(f"[Agent1] Word conversion failed: {e}")

    return file_bytes


def _clean_text(text: str) -> str:
    """
    Local rule-based text cleaning. No LLM calls.
    Removes noise, deduplicates lines, normalizes whitespace.
    """
    if not text:
        return ""

    lines = text.split("\n")
    cleaned = []
    seen = set()

    # Noise patterns to remove
    REMOVE_TOKENS = [
        "authorised signature", "authorised signatory", "for covestro",
        "confidential", "internal", "page ", "computer generated",
        "no signature required",
    ]

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip noise lines
        if any(token in stripped.lower() for token in REMOVE_TOKENS):
            continue

        # Skip pure page numbers
        if stripped.isdigit() and len(stripped) <= 3:
            continue

        # Deduplicate exact lines (common OCR artifact)
        line_key = stripped.lower()
        if line_key in seen and len(stripped) > 20:
            continue
        seen.add(line_key)

        cleaned.append(stripped)

    return "\n".join(cleaned)


def _extract_digital_text(pdf_bytes: bytes) -> tuple:
    """
    Extract text from all pages using PyMuPDF.
    Returns (total_pages, extracted_pages, raw_text, has_scanned_pages, scanned_page_indices).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    all_texts = []
    extracted_count = 0
    scanned_indices = []

    for i in range(total_pages):
        page = doc[i]
        text = page.get_text().strip()

        if text and len(text) > 10:
            # Digital page — has embedded text
            cleaned = _clean_text(text)
            if cleaned:
                all_texts.append(cleaned)
                extracted_count += 1
            else:
                # Text was entirely noise — treat as scanned
                print(f"[Agent1] Page {i+1}: text cleaned to empty ({len(text)} raw chars), treating as scanned")
                scanned_indices.append(i)
        else:
            # Scanned page — no embedded text, needs OCR
            scanned_indices.append(i)
            if text:
                print(f"[Agent1] Page {i+1}: too short ({len(text)} chars), treating as scanned")

    doc.close()

    raw_text = "\n\n" + ("\n" + "=" * 50 + "\n").join(all_texts) + "\n\n" if all_texts else ""

    return total_pages, extracted_count, raw_text, scanned_indices


async def _ocr_scanned_pages(pdf_bytes: bytes, page_indices: list) -> str:
    """
    Send scanned pages to Document AI for OCR.
    Chunks into 15-page batches (Document AI limit).
    Falls back to PyMuPDF if Document AI is unavailable.
    """
    if not page_indices:
        return ""

    MAX_PAGES_PER_REQUEST = 15
    docai = _get_docai_client()
    source_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Chunk page indices into batches of 15
    chunks = []
    for i in range(0, len(page_indices), MAX_PAGES_PER_REQUEST):
        chunks.append(page_indices[i:i + MAX_PAGES_PER_REQUEST])

    print(f"[Agent1] OCR: {len(page_indices)} scanned pages → {len(chunks)} batch(es)")

    async def _ocr_chunk(chunk_indices: list, chunk_num: int) -> str:
        """OCR a single chunk of pages."""
        # Build a PDF for this chunk
        chunk_pdf = fitz.open()
        for idx in chunk_indices:
            chunk_pdf.insert_pdf(source_doc, from_page=idx, to_page=idx)
        buf = io.BytesIO()
        chunk_pdf.save(buf)
        chunk_pdf.close()
        chunk_bytes = buf.getvalue()

        # Try Document AI
        if docai and "client" in docai:
            try:
                documentai = docai["documentai"]
                raw_doc = documentai.RawDocument(content=chunk_bytes, mime_type="application/pdf")
                request = documentai.ProcessRequest(
                    name=docai["processor_name"], raw_document=raw_doc
                )

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    _docai_executor,
                    lambda req=request: docai["client"].process_document(request=req),
                )
                text = result.document.text or ""
                print(f"[Agent1] Batch {chunk_num}: {len(chunk_indices)} pages → {len(text)} chars")
                return _clean_text(text)

            except Exception as e:
                print(f"[Agent1] Document AI batch {chunk_num} failed: {e}")

        # Fallback: return whatever PyMuPDF can get
        print(f"[Agent1] Fallback for batch {chunk_num}: {len(chunk_indices)} pages")
        fallback_doc = fitz.open(stream=chunk_bytes, filetype="pdf")
        texts = []
        for i in range(len(fallback_doc)):
            page = fallback_doc[i]
            text = page.get_text().strip()
            if text:
                texts.append(text)
        fallback_doc.close()
        return _clean_text("\n".join(texts))

    # Process chunks sequentially to respect rate limits
    results = []
    for i, chunk in enumerate(chunks):
        res = await _ocr_chunk(chunk, i + 1)
        results.append(res)
        # Small delay between batches to ensure we don't trip quotas
        if i < len(chunks) - 1:
            await asyncio.sleep(1.0)

    source_doc.close()

    # Merge all chunk results
    all_text = []
    for text in results:
        if text:
            all_text.append(text)

    return ("\n" + "=" * 50 + "\n").join(all_text)


async def smart_extract_from_file(file_bytes: bytes, mime_type: str) -> SmartExtractionResponse:
    """
    Main entry point for Agent 1. Called from routes.py.

    Simplified pipeline:
        1. Convert to PDF if needed (Word docs)
        2. Extract digital text from all pages (PyMuPDF, ~50ms)
        3. If scanned pages exist, OCR them via Document AI (~3-8s)
        4. Return merged raw_text

    Agent 2's regex engine handles splitting, classification, and extraction.
    """
    pipeline_start = time.time()

    # Step 1: Ensure PDF format
    pdf_bytes = _ensure_pdf(file_bytes)

    # Step 2: Extract digital text + identify scanned pages
    t0 = time.time()
    total_pages, extracted_count, raw_text, scanned_indices = _extract_digital_text(pdf_bytes)
    digital_time = time.time() - t0

    print(f"[Agent1] Digital extraction: {extracted_count}/{total_pages} pages "
          f"in {digital_time:.3f}s, {len(scanned_indices)} scanned pages pending")

    # Step 3: OCR scanned pages if any
    if scanned_indices:
        t1 = time.time()
        scanned_text = await _ocr_scanned_pages(pdf_bytes, scanned_indices)
        ocr_time = time.time() - t1

        if scanned_text:
            if raw_text:
                raw_text = raw_text.rstrip() + "\n" + "=" * 50 + "\n" + scanned_text + "\n\n"
            else:
                raw_text = "\n\n" + scanned_text + "\n\n"
            extracted_count += len(scanned_indices)

        print(f"[Agent1] Document AI OCR: {len(scanned_indices)} pages in {ocr_time:.2f}s")

    total_time = time.time() - pipeline_start
    print(f"\n[Agent1] ════════════════════════════════════")
    print(f"[Agent1] TOTAL: {total_time:.3f}s | "
          f"{extracted_count}/{total_pages} pages | "
          f"{len(raw_text)} chars")
    print(f"[Agent1] ════════════════════════════════════\n")

    return SmartExtractionResponse(
        total_pages=total_pages,
        extracted_pages=extracted_count,
        raw_text=raw_text,
    )
