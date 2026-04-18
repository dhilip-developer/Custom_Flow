import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.intelligence_utils import generate_llm_content, CACHE_STORE, GEMINI_MODEL_NAME

async def verify():
    print(f"--- Production Shift Verification ---")
    print(f"Target Model: {GEMINI_MODEL_NAME}")
    
    if GEMINI_MODEL_NAME != "gemini-2.5-flash-lite":
        print(f"FAIL: GEMINI_MODEL_NAME is {GEMINI_MODEL_NAME}, not gemini-2.5-flash-lite")
        return

    # Large system prompt to trigger caching (>2048 tokens in 2026)
    rules = [
        "Rule 1: Always extract the 'Container Number' accurately from the top right quadrant.",
        "Rule 2: Map the 'Total Gross Weight' to kilograms by default.",
        "Rule 3: Identify the 'Consignee' name and full industrial address.",
        "Rule 4: Extract the 'Vessel Name' and 'Voyage Number' separately.",
        "Rule 5: Detect the 'HS Code' and ensure it is 6-8 digits.",
        "Rule 6: Capture the 'Seal Number' including any alphabetical prefixes.",
        "Rule 7: Identify the 'Port of Loading' and 'Port of Discharge'.",
        "Rule 8: Extract the 'Invoice Number' and compare it with the BL number.",
        "Rule 9: List all 'Marks & Numbers' exactly as appearing.",
        "Rule 10: Sum the 'NumberOfPackages' if multiple lines exist.",
        "Rule 11: Identify any 'Hazardous Material' declarations (IMO/Class).",
        "Rule 12: Capture the 'Incoterms' (CIF, FOB, etc.).",
        "Rule 13: Extract 'Freight Payable At' location.",
        "Rule 14: Final validation - ensure the JSON structure is strictly flattened."
    ]
    # Multiply rules to exceed 2048 tokens for cache activation testing
    large_system_prompt = "\n".join(rules) * 50 
    user_prompt = "identify yourself and confirm if you are using cached context."

    print("\nAttempting first call (should create cache)...")
    response1 = await generate_llm_content(user_prompt, large_system_prompt)
    print(f"Response 1: {response1[:50]}...")
    
    if len(CACHE_STORE) > 0:
        print(f"SUCCESS: Context Cache created. Cache Store: {CACHE_STORE}")
    else:
        print("FAIL: Context Cache was not created.")

    print("\nAttempting second call (should use cache)...")
    # This should be faster and should print "Using Context Cache" in the logs
    response2 = await generate_llm_content(user_prompt, large_system_prompt)
    print(f"Response 2: {response2[:50]}...")

if __name__ == "__main__":
    asyncio.run(verify())
