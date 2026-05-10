import os
import httpx
from dotenv import load_dotenv

load_dotenv()
RENDER_API_KEY = os.getenv("RENDER_API_KEY")

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

print("Setting up Render Deployment...")

with httpx.Client() as client:
    # 1. Get Owner ID
    print("Fetching account details...")
    res = client.get("https://api.render.com/v1/owners", headers=headers)
    if res.status_code != 200:
        print("Failed to authenticate with Render API:", res.text)
        exit(1)
        
    owners = res.json()
    if not owners:
        print("No Render account found for this API key.")
        exit(1)
        
    owner_id = owners[0]["owner"]["id"]
    
    # 2. Create Service
    print("Creating web service for fire-mcp-backend...")
    payload = {
        "type": "web_service",
        "name": "fire-mcp-backend",
        "ownerId": owner_id,
        "repo": "https://github.com/vjb/FIRE",
        "branch": "master",
        "serviceDetails": {
            "env": "python",
            "plan": "free",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "python -m uvicorn src.server:app --host 0.0.0.0 --port $PORT"
            }
        }
    }
    
    res = client.post("https://api.render.com/v1/services", json=payload, headers=headers)
    
    if res.status_code == 201:
        data = res.json()
        print("\n✅ Deployment initialized successfully!")
        url = data.get('service', {}).get('serviceDetails', {}).get('url', 'Unknown URL')
        print(f"Service URL: {url}")
        print("Check your Render dashboard to see the build progress.")
    else:
        print("\n❌ Failed to create service:", res.status_code)
        print(res.text)
