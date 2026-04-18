import asyncio
from services.intelligence_utils import extract_with_super_agent
import logging
import time

logging.basicConfig(level=logging.INFO)

async def test_extraction():
    test_text_chunk = """
    INVOICE
    Invoice No.: MH2536000682
    Date: 24/02/2026
    Buyer: SEALED AIR
    Seller: Covestro India
    Total Amount: 3032800 INR
    """
    
    # Simulate a massive payload by using delimiters that the splitter uses
    test_text = "\n===========\n".join([test_text_chunk for _ in range(12)])
    
    print(f"===== STARTING BATCH TEST (Length: {len(test_text)}) =====")
    start = time.time()
    result = await extract_with_super_agent(test_text)
    duration = time.time() - start
    print(f"====== RESULT (Completed in {duration:.2f}s) ======")
    print(f"Total documents extracted: {len(result.documents)}")
    
if __name__ == "__main__":
    asyncio.run(test_extraction())
