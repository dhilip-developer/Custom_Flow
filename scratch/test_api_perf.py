import requests
import time
import json

def test_api():
    url = "http://103.148.1.182:8000/chat"
    # The subagent noted it uses application/x-www-form-urlencoded
    # and the schema is {"value": "string"}
    payload = {"value": "Hello, who are you? Please give a short 1-sentence answer."}
    
    print(f"🚀 Starting performance test for {url}...")
    
    start_time = time.time()
    try:
        # Increase timeout because subagent reported >40s
        response = requests.post(url, data=payload, timeout=120)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"✅ Request Completed in {duration:.2f} seconds.")
        
        if response.status_code == 200:
            print(f"📩 Response: {response.text}")
            # Infer speed (rough estimate)
            tokens = len(response.text.split())
            print(f"⚡ Throughput: ~{tokens/duration:.2f} words/sec")
        else:
            print(f"❌ Failed with status code {response.status_code}")
            print(f"📄 Detail: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    test_api()
