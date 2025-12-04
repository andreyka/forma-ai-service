"""Example client for the FormaAI API.

This script demonstrates how to send a prompt to the API and poll for the result.
"""

import requests
import time
import uuid
import sys

BASE_URL = "http://localhost:8001"

def generate_3d_model(prompt: str) -> None:
    """Send a generation request and poll for completion.

    Args:
        prompt (str): The description of the model to generate.
    """
    # 1. Send the request
    session_id = str(uuid.uuid4())
    payload = {
        "message": {
            "role": "ROLE_USER",
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
        state = task_data["status"]["state"]
        
        print(f"Status: {state}")
        
        if state == "TASK_STATE_COMPLETED":
            result_msg = task_data["status"]["message"]
            print("\nGeneration Complete!")
            
            # Extract file links
            for part in result_msg["parts"]:
                if part.get("file"):
                    file_info = part["file"]
                    print(f"File: {file_info['name']}")
                    print(f"Download URL: {BASE_URL}{file_info.get('fileWithUri', file_info.get('file_with_uri'))}")
            break
            
        elif state == "TASK_STATE_FAILED":
            print("Generation Failed.")
            print(task_data["status"].get("message", {}))
            break
            
        time.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Design a 10x10x10 cm cube with a 5mm hole in the center."
        
    generate_3d_model(prompt)
