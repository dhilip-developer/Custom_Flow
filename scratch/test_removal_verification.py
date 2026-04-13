
import asyncio
import json
from services.document_processor import smart_extract_from_file

async def test_extraction():
    # Load a sample file if available, or mock bytes
    # For now, let's just see if we can trigger the processor
    print("Testing Agent 1 extraction structure...")
    
    # We need some bytes. I'll check if there is a sample file in the 'documents' folder.
    # If not, this test will just be a placeholder for now until I find a file.
    
    # Actually, I can just mock the document_processor logic if I want to test the model specifically,
    # but the goal is to see the REAL output.
    
    # Let's check for files in 'documents'
    import os
    docs_dir = "documents"
    files = [f for f in os.listdir(docs_dir) if f.endswith(".pdf")] if os.path.exists(docs_dir) else []
    
    if not files:
        print("No sample PDF files found in 'documents' directory.")
        return

    sample_file = os.path.join(docs_dir, files[0])
    with open(sample_file, "rb") as f:
        file_bytes = f.read()
    
    print(f"Processing {sample_file}...")
    try:
        response = await smart_extract_from_file(file_bytes, "application/pdf")
        for doc in response.documents:
            print(f"\nDocument Type: {doc.document_type}")
            print(f"Has basic_keys: {'basic_keys' in doc.dict()}")
            if 'basic_keys' in doc.dict():
                print(f"basic_keys content: {json.dumps(doc.basic_keys, indent=2)}")
    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
