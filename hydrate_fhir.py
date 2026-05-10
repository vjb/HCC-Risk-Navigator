import httpx
import base64
import json
import asyncio

BASE_URL = "https://hapi.fhir.org/baseR4"

async def create_patient(client, name_first, name_last, gender, birth_date):
    patient = {
        "resourceType": "Patient",
        "name": [{"family": name_last, "given": [name_first]}],
        "gender": gender,
        "birthDate": birth_date
    }
    resp = await client.post(f"{BASE_URL}/Patient", json=patient)
    resp.raise_for_status()
    return resp.json()["id"]

async def create_condition(client, patient_id, code, display):
    condition = {
        "resourceType": "Condition",
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": code, "display": display}]}
    }
    resp = await client.post(f"{BASE_URL}/Condition", json=condition)
    resp.raise_for_status()
    return resp.json()["id"]

async def create_document(client, patient_id, text_content):
    b64_content = base64.b64encode(text_content.encode("utf-8")).decode("utf-8")
    doc = {
        "resourceType": "DocumentReference",
        "status": "current",
        "subject": {"reference": f"Patient/{patient_id}"},
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": b64_content
            }
        }]
    }
    resp = await client.post(f"{BASE_URL}/DocumentReference", json=doc)
    resp.raise_for_status()
    return resp.json()["id"]

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Patient 1: Tamara Williams (Diabetic Neuropathy Gap)
        p1_id = await create_patient(client, "Tamara", "Williams", "female", "1958-04-12")
        await create_condition(client, p1_id, "E11.9", "Type 2 diabetes mellitus without complications")
        text1 = "Patient presents for routine follow up of type 2 diabetes. She reports severe burning and tingling in both feet, especially at night. Monofilament testing reveals loss of protective sensation. Assessment: Diabetic peripheral neuropathy. Plan: Start Gabapentin 300mg QHS."
        await create_document(client, p1_id, text1)
        print(f"Created Patient 1 (Neuropathy Gap): {p1_id}")

        # Patient 2: Richard Chen (COPD Exacerbation Gap)
        p2_id = await create_patient(client, "Richard", "Chen", "male", "1945-08-22")
        await create_condition(client, p2_id, "J44.9", "Chronic obstructive pulmonary disease, unspecified")
        text2 = "Patient comes in with increased dyspnea, increased sputum purulence, and increased cough over the last 3 days. O2 sats are 89% on room air. Assessment: Acute exacerbation of COPD. Plan: Prescribe 5-day course of Prednisone and Z-Pak."
        await create_document(client, p2_id, text2)
        print(f"Created Patient 2 (COPD Exacerbation Gap): {p2_id}")

        # Patient 3: Maria Gonzalez (CKD Stage 4 Gap)
        p3_id = await create_patient(client, "Maria", "Gonzalez", "female", "1962-11-05")
        await create_condition(client, p3_id, "N18.9", "Chronic kidney disease, unspecified")
        text3 = "Follow up for chronic kidney disease. Recent labs show eGFR of 22 mL/min/1.73m2, which has been stable for 6 months. Assessment: Stage 4 chronic kidney disease. Plan: Continue current renoprotective management and refer to nephrology."
        await create_document(client, p3_id, text3)
        print(f"Created Patient 3 (CKD Stage 4 Gap): {p3_id}")

        with open("demo_patient_ids.txt", "w") as f:
            f.write(f"{p1_id},{p2_id},{p3_id}")

if __name__ == "__main__":
    asyncio.run(main())
