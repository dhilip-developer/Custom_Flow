from pydantic import BaseModel, Field
from enum import Enum
from typing import Any, List, Dict, Optional
import asyncio

class DocumentType(str, Enum):
    BOL = "Bill of Lading (BOL)"
    INVOICE = "Invoice"
    PACKING_LIST = "Packing List"
    FREIGHT_CERTIFICATE = "Freight Certificate"
    INSURANCE_CERTIFICATE = "Insurance Certificate"
    HSS_AGREEMENT = "High Sea Sale Agreement (HSS)"
    COO = "Certificate of Origin"
    COA = "Certificate of Analysis"
    WEIGHT_NOTE = "Weight Note"
    IEC_CERTIFICATE = "IEC Certificate"
    GST_CERTIFICATE = "GST Certificate"
    PAN_CARD = "PAN Card"
    AUTH_LETTER = "Authorization Letter"
    LEGAL_DOCUMENT = "Legal Agreement / Affidavit"
    ADDITIONAL = "Additional Documents"
    UNKNOWN = "Unknown Document"
    SKIP = "Skip / Junk Page"

class ClassificationResponse(BaseModel):
    document_type: str = Field(..., description="The classified type of the document")
    confidence: float = Field(..., description="The confidence level of the classification (between 0.0 and 100.0)")

class DataExtractionRequest(BaseModel):
    document_type: str = Field(..., description="The classification decided by Agent 2 (e.g. 'Invoice', 'Bill of Lading (BOL)')")
    text: str = Field(..., description="The raw untampered OCR text chunk yielded by Agent 1")

class DataExtractionResponse(BaseModel):
    extracted_data: Dict[str, Any] = Field(..., description="A mapping of rigorously structured JSON keys explicitly paired to their physical mapped values")


class BatchExtractionItem(BaseModel):
    page_range: str = Field(..., description="Page range of the document")
    document_type: str = Field(..., description="Classified document type")
    extracted_data: Dict[str, Any] = Field(..., description="Extracted key-values for this document")


class BatchDataExtractionResponse(BaseModel):
    results: List[BatchExtractionItem] = Field(..., description="List of extracted data for each document in the batch")


class FreightCertificateCheckResponse(BaseModel):
    freight_certificate_required: str = Field(..., description="'needed' if a Freight Certificate is required, 'not needed' if it is not")
    status_label: str = Field(..., description="Human-readable status: 'Required' or 'Not Required'")
    reason: str = Field(..., description="Detailed explanation for the decision")
    confidence: float = Field(..., description="Confidence level of the decision (0.0 to 100.0)")


class DocumentItem(BaseModel):
    filename: str = Field(..., description="Original filename of the attachment")
    mime_type: str = Field(..., description="MIME type of the document (e.g. application/pdf, image/jpeg)")
    size_bytes: int = Field(..., description="File size in bytes")
    saved_path: str = Field(..., description="Local server path where the file was safely stored")


class EmailItem(BaseModel):
    email_subject: str = Field(..., description="Subject line of the email")
    email_date: str = Field(..., description="Date the email was received")
    source_account: str = Field(..., description="Which inbox the email was found in: 'Gmail' or 'Zoho'")
    documents: List[DocumentItem] = Field(..., description="List of document attachments contained within this email")


class EmailScanResponse(BaseModel):
    sender_email: str = Field(..., description="The email address that was searched for")
    accounts_scanned: List[str] = Field(..., description="List of inbox accounts that were scanned")
    total_emails_found: int = Field(..., description="Total number of emails found FROM this sender across all accounts")
    total_documents_found: int = Field(..., description="Total number of document attachments retrieved")
    account_errors: Optional[List[str]] = Field(None, description="Any connection/authentication errors encountered per account (null if none)")
    emails: List[EmailItem] = Field(..., description="A list of processed emails, each containing their parsed metadata and grouped file attachments.")


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1: Smart OCR Extraction Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExtractedDocument(BaseModel):
    document_type: str = Field(..., description="Classified document type (Invoice, BOL, HSS, etc.)")
    page_range: str = Field(..., description="Page range in the original PDF, e.g. '1-3' or '4'")
    text: str = Field(..., description="Full OCR text of all pages belonging to this document group")


class SmartExtractionResponse(BaseModel):
    total_pages: int = Field(..., description="Total number of pages in the uploaded PDF")
    extracted_pages: int = Field(..., description="Number of pages from which text was successfully retrieved")
    raw_text: str = Field(..., description="The complete merged raw string of all extracted document text")


class PageIdentification(BaseModel):
    """Internal model for Gemini-based page labeling."""
    page_number: int
    document_type: str
    is_new_document: bool = Field(True, description="True if this page starts a new document, False if it is a continuation of the previous page.")
    confidence: float
    reasoning: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Agent 5: Document Cross-Verification Schemas
# ─────────────────────────────────────────────────────────────────────────────

class FieldComparisonResult(BaseModel):
    field_name: str = Field(..., description="Human-readable name of the field comparison (e.g. 'HS CODE — BOL vs Invoice')")
    documents_compared: List[str] = Field(..., description="The two document types being compared")
    values: Dict[str, Any] = Field(..., description="The actual values found in each document for this field")
    status: str = Field(..., description="MATCH, MISMATCH, or UNVERIFIABLE")
    discrepancy_note: Optional[str] = Field(None, description="Present only on MISMATCH — explains what differs and why it matters")


class SkippedComparison(BaseModel):
    field_name: str = Field(..., description="Human-readable name of the skipped comparison")
    reason: str = Field(..., description="Why this comparison was skipped (document not provided, both fields empty, etc.)")


class ComparisonTableRow(BaseModel):
    field_name: str = Field(..., description="The field being compared (e.g. 'HS CODE', 'GROSS WEIGHT')")
    bill_of_lading: Optional[str] = Field(None, description="Value from Bill of Lading (or N/A if not provided)")
    invoice: Optional[str] = Field(None, description="Value from Invoice (or N/A if not provided)")
    packing_list: Optional[str] = Field(None, description="Value from Packing List (or N/A if not provided)")
    freight_certificate: Optional[str] = Field(None, description="Value from Freight Certificate (or N/A if not provided)")
    insurance_certificate: Optional[str] = Field(None, description="Value from Insurance Certificate (or N/A if not provided)")
    verdict: str = Field(..., description="MATCH | MISMATCH | UNVERIFIABLE | N/A")
    discrepancy_note: Optional[str] = Field(None, description="Explanation if verdict is MISMATCH")


class CrossVerificationResponse(BaseModel):
    overall_verdict: str = Field(..., description="COHERENT | DISCREPANCIES FOUND | INSUFFICIENT DATA")
    coherence_score: float = Field(..., description="Percentage of verifiable fields that matched (0.0 to 100.0)")
    documents_provided: List[str] = Field(..., description="List of document types that were submitted for comparison")
    summary: str = Field(..., description="One-sentence professional summary of the cross-verification result")
    comparison_table: List[ComparisonTableRow] = Field(..., description="Full side-by-side table of every field comparison across all documents")
    matched_fields: List[FieldComparisonResult] = Field(..., description="All field comparisons where values were consistent across documents")
    mismatched_fields: List[FieldComparisonResult] = Field(..., description="All field comparisons where values differed — these require attention")
    skipped_comparisons: List[SkippedComparison] = Field(..., description="Comparisons that could not be performed due to missing documents or empty fields")
# ─────────────────────────────────────────────────────────────────────────────
# Agent 3: Batch Data Extraction Request Schema
# ─────────────────────────────────────────────────────────────────────────────

class BatchDataExtractionRequest(BaseModel):
    extraction_results: SmartExtractionResponse = Field(..., description="The complete output from Agent 1 (OCR Extractor)")


# ─────────────────────────────────────────────────────────────────────────────
# Super Agent: Merged Classification & Extraction
# ─────────────────────────────────────────────────────────────────────────────

class SuperExtractionResult(BaseModel):
    document_type: str = Field(..., description="The classified type of this document segment")
    structured_data: Dict[str, Any] = Field(..., description="The extracted data fields based on the type")


class SuperExtractionResponse(BaseModel):
    documents: List[SuperExtractionResult] = Field(..., description="List of all logical documents found in the text")


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing: Document Cleaning Assistant Schemas
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3: Data Verification Schemas
# ─────────────────────────────────────────────────────────────────────────────

class VerificationRequest(BaseModel):
    document_type: str = Field(..., description="The type from Agent 2")
    extracted_data: Dict[str, Any] = Field(..., description="The structured fields from Agent 2")

class VerificationResponse(BaseModel):
    status: str = Field(..., description="VERIFIED | FAILED | PARTIAL")
    confidence: float = Field(..., description="Confidence score (0-100)")
    document_name: str = Field(..., description="Verified name of the document")
    details: str = Field(..., description="Explanation of verification results")
    fields_verified: int = Field(..., description="Number of mandatory fields found and verified")


class BatchVerificationRequest(BaseModel):
    documents: List[VerificationRequest]


class BatchVerificationResponse(BaseModel):
    total_verified: int
    results: List[VerificationResponse]


class CustomsIntelligenceResult(BaseModel):
    document_type: str = Field(..., description="Type of the document from input")
    total_fields: int = Field(..., description="Number of required fields for this type")
    found_fields: int = Field(..., description="Number of required fields present and non-null")
    missing_fields: List[str] = Field(..., description="List of names of missing required fields")
    confidence_score: int = Field(..., description="Confidence score rounded to nearest integer")
    warnings: List[str] = Field(..., description="Minor logical or data warnings")
    critical_issues: List[str] = Field(default_factory=list, description="Major blockers found in this document")

class GlobalValidationResult(BaseModel):
    missing_documents: List[str] = Field(..., description="Required documents not present in input")
    cross_document_issues: List[str] = Field(..., description="Discrepancies found across documents")
    critical_issues: List[str] = Field(default_factory=list, description="Aggregated critical issues from all docs")
    warnings: List[str] = Field(default_factory=list, description="Aggregated warnings from all docs")
    overall_confidence: int = Field(..., description="Final confidence score after penalties")
    clearance_ready: bool = Field(..., description="True only if zero critical issues and all mandatory docs present")

class CustomsIntelligenceResponse(BaseModel):
    documents: List[CustomsIntelligenceResult]
    global_validation: GlobalValidationResult

class CustomsAuditRequest(BaseModel):
    documents: List[Dict[str, Any]] = Field(..., description="List of documents from Agent 2 with document_type and structured_data")

class CleanedDocumentResponse(BaseModel):
    type: str = Field(..., description="The type hint provided (e.g. 'invoice')")
    cleaned_text: str = Field(..., description="The cleaned and readable text")
