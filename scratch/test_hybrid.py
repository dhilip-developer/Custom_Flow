import asyncio
from services.intelligence_utils import extract_with_super_agent

async def main():
    text = "Invoice No: 123 Total Amount: 100 Buyer: Me"
    print("Testing extract_with_super_agent")
    result = await extract_with_super_agent(text)
    print("Result:", result)

asyncio.run(main())
