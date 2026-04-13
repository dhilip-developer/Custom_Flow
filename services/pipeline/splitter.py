import fitz  # PyMuPDF
import io
import time
import os
from typing import List, Dict
try:
    import aspose.words as aw
except ImportError:
    aw = None


class DocumentSplitter:
    """
    V3 Splitter: Splits PDF into pages, extracts text AND generates
    thumbnails for EVERY page (needed for batch vision classification).
    Now supports transparent .doc and .docx conversion.
    """

    @staticmethod
    def _ensure_pdf(file_bytes: bytes) -> bytes:
        """
        Detects if bytes are Word doc/docx and converts to PDF if necessary.
        """
        if not file_bytes:
            return file_bytes

        # Header detection
        is_pdf = file_bytes.startswith(b"%PDF-")
        is_docx = file_bytes.startswith(b"PK\x03\x04")
        is_doc_legacy = file_bytes.startswith(b"\xd0\xcf\x11\xe0")

        if is_pdf:
            return file_bytes

        if (is_docx or is_doc_legacy) and aw:
            print(f"[Splitter] Detected Word document ({'DOCX' if is_docx else 'DOC'}). Converting to PDF...")
            try:
                # Load from bytes
                doc_stream = io.BytesIO(file_bytes)
                doc = aw.Document(doc_stream)
                
                # Save to PDF bytes
                pdf_stream = io.BytesIO()
                # Use PDF save options if needed, but default is usually fine
                doc.save(pdf_stream, aw.SaveFormat.PDF)
                print(f"[Splitter] Word conversion successful.")
                return pdf_stream.getvalue()
            except Exception as e:
                print(f"[Splitter] Word conversion failed: {e}. Attempting direct open...")
                return file_bytes
        
        if not is_pdf and not aw:
            print("[Splitter] WARNING: Received non-PDF file but aspose-words is not installed.")
            
        return file_bytes

    @staticmethod
    def split(file_bytes: bytes) -> List[Dict]:
        """
        Returns list of page dicts with:
        - page_number: 1-indexed
        - text: raw digital text (may be empty for scanned docs)
        - image_bytes: JPG thumbnail for vision classification (ALWAYS generated)
        - buffer: single-page PDF bytes for targeted OCR later
        """
        start = time.time()
        
        # Ensure we are working with PDF bytes
        pdf_bytes = DocumentSplitter._ensure_pdf(file_bytes)
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            print(f"[Splitter] Fatal Error: Could not open document stream: {e}")
            raise RuntimeError(f"Failed to open document stream. Ensure file is a valid PDF or Word document. Error: {e}")
            
        pages: List[Dict] = []

        for i in range(len(doc)):
            page = doc[i]

            # 1. Extract digital text layer (fast, may be empty for scans)
            text = page.get_text().strip()

            # 2. Generate thumbnail for EVERY page (batch vision needs it)
            #    150 DPI balances quality vs size (~30-50KB per page)
            pix = page.get_pixmap(dpi=150)
            image_bytes = pix.tobytes("jpeg")

            # 3. Create single-page PDF buffer for later targeted OCR
            single = fitz.open()
            single.insert_pdf(doc, from_page=i, to_page=i)
            buf = io.BytesIO()
            single.save(buf)
            single.close()

            pages.append({
                "page_number": i + 1,
                "text": text,
                "image_bytes": image_bytes,
                "buffer": buf.getvalue(),
            })

        doc.close()
        elapsed = time.time() - start
        print(f"[Splitter] {len(pages)} pages split in {elapsed:.2f}s "
              f"(avg {len(pages) and elapsed/len(pages)*1000:.0f}ms/page)")
        return pages
