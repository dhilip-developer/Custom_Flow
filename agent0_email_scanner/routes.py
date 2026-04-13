"""
Routes for Agent 0: Email Document Retriever
"""
from fastapi import APIRouter, HTTPException, Query
from models.schemas import EmailScanResponse
import services.email_scanner as email_scanner

router = APIRouter()


@router.post(
    "/scan-email",
    response_model=EmailScanResponse,
    tags=["Agent 0: Email Document Retriever"]
)
async def scan_email(
    sender_email: str = Query(
        ...,
        description="The email address to search for. Both Gmail and Zoho inboxes will be scanned for emails FROM this address and all attachments will be returned.",
        examples=["customer@example.com"]
    )
):
    """
    Agent 0: Enter a sender's email address and this agent will scan both configured inboxes
    (**Gmail**: boostentryai@gmail.com and **Zoho**: ctalert@workboosterai.com) for any emails
    received FROM that address.

    All document attachments (PDFs, images, Word docs, Excel files) are extracted and
    returned as **Base64-encoded content** in the response body, ready to be passed
    directly into the downstream pipeline:

    - **Agent 1** `/extract-text` → OCR / text extraction
    - **Agent 2** `/classify-text` → document classification  
    - **Agent 3** `/extract-data` → structured data extraction
    - **Agent 4** `/detect-freight-certificate` → freight requirement detection
    """
    if not sender_email or "@" not in sender_email:
        raise HTTPException(
            status_code=400,
            detail="Invalid email address provided. Please supply a valid email address (e.g. customer@example.com)."
        )

    result = email_scanner.scan_email_for_documents(sender_email.strip().lower())

    return EmailScanResponse(
        sender_email=result["sender_email"],
        accounts_scanned=result["accounts_scanned"],
        total_emails_found=result["total_emails_found"],
        total_documents_found=result["total_documents_found"],
        account_errors=result["account_errors"],
        emails=[
            {
                "email_subject": email_obj["email_subject"],
                "email_date": email_obj["email_date"],
                "source_account": email_obj["source_account"],
                "documents": [
                    {
                        "filename": doc["filename"],
                        "mime_type": doc["mime_type"],
                        "size_bytes": doc["size_bytes"],
                        "saved_path": doc["saved_path"],
                    }
                    for doc in email_obj["documents"]
                ]
            }
            for email_obj in result.get("emails", [])
        ]
    )
