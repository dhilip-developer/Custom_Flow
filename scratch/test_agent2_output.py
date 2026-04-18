import asyncio
from services.intelligence_utils import extract_chunk_with_gemini
import json

async def main():
    text = """
    COMMERCIAL INVOICE
    Invoice No: INV-2023-001
    Date: 2023-10-25
    Seller: Acme Corp
    Buyer: Wayne Enterprises
    Total Amount: 1500.00 USD
    Items:
    1x Batmobile Engine - 1500.00
    """
    res = await extract_chunk_with_gemini(text, "unknown")
    print(json.dumps(res, indent=2))

asyncio.run(main())
