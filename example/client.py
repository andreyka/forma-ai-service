import requests
import time
import uuid
import sys

BASE_URL = "http://localhost:8001"

def generate_model(prompt):
    # 1. Send the request
    session_id = str(uuid.uuid4())
    payload = {
        "message": {
            "role": "user",
            "parts": [{"text": prompt}],
            "context_id": session_id
        }
    }
    
    print(f"Sending prompt: {prompt}")
    try:
        response = requests.post(f"{BASE_URL}/v1/message:send", json=payload)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}. Is the service running?")
        return
    
    task = response.json()["task"]
    task_id = task["id"]
    print(f"Task started. ID: {task_id}")

    # 2. Poll for completion
    while True:
        status_resp = requests.get(f"{BASE_URL}/v1/tasks/{task_id}")
        status_resp.raise_for_status()
        task_data = status_resp.json()["task"]
        state = task_data["state"]
        
        print(f"Status: {state}")
        
        if state == "COMPLETED":
            result_msg = task_data["result"]
            print("\nGeneration Complete!")
            
            # Extract file links
            for part in result_msg["parts"]:
                if "file" in part:
                    file_info = part["file"]
                    print(f"File: {file_info['name']}")
                    print(f"Download URL: {BASE_URL}{file_info['file_with_uri']}")
            break
            
        elif state == "FAILED":
            print("Generation Failed.")
            print(task_data.get("result", {}))
            break
            
        time.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Design a 10x10x10 cm cube with a 5mm hole in the center."
        
    generate_model(prompt)
