
import os
import imaplib
import email
from email.header import decode_header
import re
from shared.config import EMAIL_ACCOUNTS

def sanitize_folder_name(name: str) -> str:
    """Replaces illegal folder characters with underscores."""
    if not name: return "unknown"
    return re.sub(r'[\\/*?:"<>| +:]', '_', str(name))

def _decode_header_value(value):
    """Safely decode email headers like Subject or Date."""
    if not value:
        return ""
    try:
        decoded_parts = decode_header(value)
        header_text = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                header_text += part.decode(encoding if encoding else "utf-8", errors="replace")
            else:
                header_text += str(part)
        return header_text
    except Exception:
        return str(value)

def scan_email_for_documents(sender_email: str) -> dict:
    accounts_scanned = []
    account_errors = []
    emails = []
    total_emails_found = 0
    total_documents_found = 0
    
    # Simple deduplication set to avoid counting the same email in multiple folders
    seen_message_ids = set()

    # Ensure root documents directory exists
    root_docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "documents")
    os.makedirs(root_docs_dir, exist_ok=True)

    for account_name, config in EMAIL_ACCOUNTS.items():
        accounts_scanned.append(account_name)
        
        if not config["password"]:
            account_errors.append(f"No app password found for {account_name}.")
            continue

        try:
            # Connect to IMAP securely
            mail = imaplib.IMAP4_SSL(config["imap_server"])
            mail.login(config["email"], config["password"])
            
            # Robust logic: Scan through multiple folders (Inbox, All Mail, Spam)
            for folder in config.get("folders", ["INBOX"]):
                try:
                    # Select folder with quotes to handle spaces (e.g. "[Gmail]/All Mail")
                    status, _ = mail.select(f'"{folder}"', readonly=True)
                    if status != "OK": continue

                    # Search for emails FROM the specified sender
                    status, messages = mail.search(None, f'FROM "{sender_email}"')
                    if status != "OK": continue
                        
                    email_ids = messages[0].split()
                    
                    for e_id in email_ids:
                        status, msg_data = mail.fetch(e_id, "(RFC822)")
                        if status != "OK": continue
                        
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                # Use Message-ID for absolute deduplication across folders
                                msg_id = msg.get("Message-ID")
                                if msg_id in seen_message_ids: continue
                                seen_message_ids.add(msg_id)
                                
                                total_emails_found += 1
                                
                                # Safely decode the subject and date
                                subject_str = _decode_header_value(msg.get("Subject", "No Subject"))
                                email_date = _decode_header_value(msg.get("Date", "Unknown Date"))
                                
                                # Generate the folder path for this specific email (Hiba Structure)
                                sanitized_date = sanitize_folder_name(email_date)
                                email_folder_name = f"{sender_email.replace('@', '_at_')}_{sanitized_date}"
                                email_dir_path = os.path.join(root_docs_dir, email_folder_name)
                                
                                email_docs = []

                                # Walk through the email parts to find attachments
                                for part in msg.walk():
                                    if part.get_content_maintype() == 'multipart': continue
                                    if part.get('Content-Disposition') is None: continue

                                    filename = part.get_filename()
                                    if filename is None: continue

                                    # Decode filename safely
                                    filename_str = _decode_header_value(filename)
                                    payload = part.get_payload(decode=True)
                                    if not payload: continue
                                        
                                    # Create directory physically only if an attachment is found
                                    os.makedirs(email_dir_path, exist_ok=True)
                                    
                                    # Save the file physically
                                    safe_filename = sanitize_folder_name(filename_str)
                                    file_path = os.path.join(email_dir_path, safe_filename)
                                    with open(file_path, "wb") as f:
                                        f.write(payload)

                                    email_docs.append({
                                        "filename": filename_str,
                                        "mime_type": part.get_content_type(),
                                        "size_bytes": len(payload),
                                        "saved_path": file_path
                                    })
                                    total_documents_found += 1
                                
                                if email_docs:
                                    emails.append({
                                        "email_subject": subject_str,
                                        "email_date": email_date,
                                        "source_account": account_name,
                                        "documents": email_docs
                                    })
                except Exception as folder_err:
                    print(f"Skipping folder {folder} on {account_name}: {folder_err}")
            
            mail.logout()

        except imaplib.IMAP4.error as e:
            account_errors.append(f"Authentication failed for {account_name}: {e}")
        except Exception as e:
            account_errors.append(f"Error processing {account_name}: {str(e)}")

    return {
        "sender_email": sender_email,
        "accounts_scanned": accounts_scanned,
        "total_emails_found": total_emails_found,
        "total_documents_found": total_documents_found,
        "account_errors": account_errors if account_errors else None,
        "emails": emails
    }
