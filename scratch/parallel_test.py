import requests
import time
import os

def test_llm():
    url = "http://103.148.1.182:8000/chat"
    payload = {"value": "Test request for benchmark. Please reply with 'OK'."}
    start = time.time()
    try:
        response = requests.post(url, data=payload, timeout=120)
        return time.time() - start, response.text
    except Exception as e:
        return None, str(e)

def test_paddle_ocr():
    url = "http://103.148.1.182:8000/paddle_ocr"
    # Use the header.png found in gateway_ui
    img_path = r"c:\Users\dk637\OneDrive\Desktop\Custom-flow\customs_flow_agents(Dhilip)\gateway_ui\static\images\header.png"
    
    if not os.path.exists(img_path):
        return None, "Test image not found"
        
    start = time.time()
    try:
        with open(img_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, timeout=60)
            return time.time() - start, response.text
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    print("🚦 Starting Parallel Test...")
    
    llm_time, llm_res = test_llm()
    print(f"🧠 LLM Test: {llm_time:.2f}s" if llm_time else f"❌ LLM Failed: {llm_res}")
    
    ocr_time, ocr_res = test_paddle_ocr()
    print(f"👁️ OCR Test: {ocr_time:.2f}s" if ocr_time else f"❌ OCR Failed: {ocr_res}")
