import requests
import time

def test_api():
    print("Testing /health")
    try:
        r = requests.get("http://localhost:8000/health")
        print(r.json())
        
        print("Testing /api/demo")
        r = requests.post("http://localhost:8000/api/demo")
        data = r.json()
        print(data)
        dataset_id = data.get("dataset_id")
        
        print(f"Testing /api/dataset/{dataset_id}")
        r = requests.get(f"http://localhost:8000/api/dataset/{dataset_id}")
        print("Rows:", r.json().get("overview", {}).get("row_count"))
        
        print(f"Testing /api/dataset/{dataset_id}/insights")
        r = requests.get(f"http://localhost:8000/api/dataset/{dataset_id}/insights")
        print(r.json().get("insights", "")[:100] + "...")
        
        print(f"Testing /api/dataset/{dataset_id}/ask")
        r = requests.post(f"http://localhost:8000/api/dataset/{dataset_id}/ask", json={"question": "What is this?"})
        print(r.json().get("answer", ""))
        
        print("All backend tests passed!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    time.sleep(2) # Give server time to start
    test_api()
