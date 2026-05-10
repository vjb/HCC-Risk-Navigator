import asyncio
import httpx

HCC_SEARCH_CODES = [
    "E11.9", "E11.40", "E11.65", "I50.9", "I50.32", "N18.3", "N18.4", "J44.1", "F32.9"
]

async def check():
    base = "https://hapi.fhir.org/baseR4"
    print("Fetching DocumentReferences from HAPI FHIR...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{base}/DocumentReference?_count=100")
        if resp.status_code != 200:
            print("Failed to fetch DocumentReferences", resp.status_code)
            return
            
        data = resp.json()
        patients_with_notes = set()
        for entry in data.get("entry", []):
            ref = entry.get("resource", {}).get("subject", {}).get("reference", "")
            if ref.startswith("Patient/"):
                patients_with_notes.add(ref.split("/")[1])
                
        print(f"Found {len(patients_with_notes)} patients with notes.")
        
        found_match = False
        for pid in list(patients_with_notes)[:50]:
            c_resp = await client.get(f"{base}/Condition?subject=Patient/{pid}")
            if c_resp.status_code == 200:
                c_data = c_resp.json()
                for entry in c_data.get("entry", []):
                    code_concept = entry.get("resource", {}).get("code", {})
                    for coding in code_concept.get("coding", []):
                        code = coding.get("code")
                        if code in HCC_SEARCH_CODES:
                            print(f"✅ BINGO! Patient {pid} has clinical notes AND condition {code}!")
                            # Let's fetch the actual note to see if it has text
                            d_resp = await client.get(f"{base}/DocumentReference?subject=Patient/{pid}")
                            d_data = d_resp.json()
                            for d_entry in d_data.get("entry", []):
                                doc = d_entry.get("resource", {})
                                content = doc.get("content", [])
                                if content:
                                    attachment = content[0].get("attachment", {})
                                    data_text = attachment.get("data")
                                    if data_text:
                                        print(f"   -> Note contains base64 data. Length: {len(data_text)}")
                                        found_match = True
                                        return
                            
        if not found_match:
            print("❌ No patients found in HAPI FHIR with both clinical notes containing data and an HCC condition.")

if __name__ == "__main__":
    asyncio.run(check())
