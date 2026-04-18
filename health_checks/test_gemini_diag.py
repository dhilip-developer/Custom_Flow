import asyncio
from services.intelligence_utils import extract_with_super_agent
import logging

logging.basicConfig(level=logging.DEBUG)

async def test_extraction():
    test_text = """
    INVOICE
    Invoice No.: MH2536000682
    Date: 24/02/2026
    Buyer: SEALED AIR
    Seller: Covestro India
    Total Amount: 3032800 INR
    """
    
    print("===== STARTING DIRECT TEST =====")
    result = await extract_with_super_agent(test_text)
    print("====== RESULT ======")
    print(result.dict())
    
if __name__ == "__main__":
    asyncio.run(test_extraction())
