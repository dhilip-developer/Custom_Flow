
from models.schemas import ExtractedDocument, CleanedDocumentResponse
from pydantic import ValidationError

print("Verifying schema removals...")

# Test ExtractedDocument
try:
    doc = ExtractedDocument(
        document_type="Invoice",
        page_range="1",
        text="Sample text",
        basic_keys={"invoice_number": "123"}
    )
    print("FAILED: ExtractedDocument still accepts basic_keys!")
except ValidationError as e:
    print("SUCCESS: ExtractedDocument rejected basic_keys as expected.")

# Test CleanedDocumentResponse
try:
    resp = CleanedDocumentResponse(
        type="Invoice",
        cleaned_text="Sample text",
        key_values={"invoice_number": "123"}
    )
    print("FAILED: CleanedDocumentResponse still accepts key_values!")
except ValidationError as e:
    print("SUCCESS: CleanedDocumentResponse rejected key_values as expected.")

print("\nVerification of structural changes complete.")
