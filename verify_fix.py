"""Verification of restored compatibility in services/document_processor.py"""
try:
    from services.document_processor import generate_gemini_content_with_retry, classify_document
    print("[SUCCESS] Import successful: generate_gemini_content_with_retry, classify_document")
    
    # Test classify_document attribute
    import services.document_processor as proc
    if hasattr(proc, 'classify_document'):
        print("[SUCCESS] Attribute exists: services.document_processor.classify_document")
    else:
        print("[FAILURE] Attribute missing: services.document_processor.classify_document")
        
except Exception as e:
    print(f"[FAILURE] Error during verification: {e}")
