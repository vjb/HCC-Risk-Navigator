import httpx
import asyncio

BASE_URL = "https://hapi.fhir.org/baseR4"
PATIENTS = ["132026010", "132026013", "132026016"]

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        for pid in PATIENTS:
            print(f"\nChecking Patient {pid}...")
            
            p_resp = await client.get(f"{BASE_URL}/Patient/{pid}")
            print(f"  Patient HTTP Status: {p_resp.status_code}")
            
            c_resp = await client.get(f"{BASE_URL}/Condition?subject=Patient/{pid}")
            c_count = len(c_resp.json().get('entry', [])) if c_resp.status_code == 200 else 0
            print(f"  Conditions HTTP Status: {c_resp.status_code} | Found: {c_count}")
            
            d_resp = await client.get(f"{BASE_URL}/DocumentReference?subject=Patient/{pid}")
            d_count = len(d_resp.json().get('entry', [])) if d_resp.status_code == 200 else 0
            print(f"  Documents HTTP Status: {d_resp.status_code} | Found: {d_count}")

if __name__ == "__main__":
    asyncio.run(main())
