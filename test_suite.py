"""
Test suite using FastAPI TestClient to test all endpoints in-process without network overhead.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    passed = 0
    failed = 0

    print("=" * 60)
    print("RUNNING IN-PROCESS TEST CLIENT SUITE")
    print("=" * 60)

    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}
    print("PASS: Health check (200)")
    passed += 1

    # 2. GET /patients (seed records)
    res = client.get("/patients")
    assert res.status_code == 200
    body = res.json()
    assert body["error"] is None
    assert len(body["data"]) >= 2
    print(f"PASS: GET /patients returned {len(body['data'])} records")
    passed += 1

    # 3. GET /patients/{id} (seed record 1)
    patient_id = body["data"][0]["patient_id"]
    res = client.get(f"/patients/{patient_id}")
    assert res.status_code == 200
    assert res.json()["data"]["patient_id"] == patient_id
    assert "/" in res.json()["data"]["date_of_birth"]  # formatted as MM/DD/YYYY
    print("PASS: GET /patients/{id} by UUID with formatted DOB")
    passed += 1

    # 4. GET /patients/{id} (404 check)
    res = client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    assert res.json()["data"] is None
    assert "not found" in res.json()["error"]
    print("PASS: GET /patients/{id} 404 with strict envelope")
    passed += 1

    # 5. POST /patients (Create record)
    new_patient = {
        "first_name": "Marcus",
        "last_name": "Aurelius",
        "date_of_birth": "04/26/1980",
        "sex": "Male",
        "phone_number": "5559998888",
        "email": "marcus@rome.org",
        "address_line_1": "1 Palatine Hill",
        "city": "Rome",
        "state": "NY",
        "zip_code": "10001",
        "insurance_provider": "Empire Blue",
        "insurance_member_id": "EMP12345",
        "preferred_language": "English",
        "emergency_contact_name": "Lucius Verus",
        "emergency_contact_phone": "5557776666"
    }
    res = client.post("/patients", json=new_patient)
    assert res.status_code == 201
    created = res.json()
    assert created["error"] is None
    created_id = created["data"]["patient_id"]
    assert created["data"]["first_name"] == "Marcus"
    assert created["data"]["date_of_birth"] == "04/26/1980"
    print("PASS: POST /patients created record with 201 and strict envelope")
    passed += 1

    # 6. GET /patients filter by phone
    res = client.get("/patients?phone_number=5559998888")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1
    assert res.json()["data"][0]["patient_id"] == created_id
    print("PASS: GET /patients?phone_number filter works")
    passed += 1

    # 7. PUT /patients/{id} (Partial update)
    update_payload = {"city": "New Rome", "state": "CA"}
    res = client.put(f"/patients/{created_id}", json=update_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["data"]["city"] == "New Rome"
    assert updated["data"]["state"] == "CA"
    assert updated["data"]["first_name"] == "Marcus"  # unchanged
    print("PASS: PUT /patients/{id} partial update works")
    passed += 1

    # 8. DELETE /patients/{id} (Soft delete)
    res = client.delete(f"/patients/{created_id}")
    assert res.status_code == 200
    assert res.json()["data"] is None
    assert res.json()["error"] is None
    print("PASS: DELETE /patients/{id} soft-deleted")
    passed += 1

    # 9. Verify soft-deleted patient is not in list and returns 404 on get
    res = client.get(f"/patients/{created_id}")
    assert res.status_code == 404
    assert res.json()["data"] is None
    res = client.get("/patients?phone_number=5559998888")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 0
    print("PASS: Soft-deleted patient excluded from GET and list queries")
    passed += 1

    # 10. Validation error: Future DOB
    bad_payload = new_patient.copy()
    bad_payload["date_of_birth"] = "01/01/2099"
    res = client.post("/patients", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["data"] is None
    assert "date_of_birth" in res.json()["error"]
    print("PASS: Validation error on future DOB returns 422 with clean envelope")
    passed += 1

    # 11. Validation error: Invalid Name regex
    bad_payload = new_patient.copy()
    bad_payload["first_name"] = "Marcus123"
    res = client.post("/patients", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["data"] is None
    assert "first_name" in res.json()["error"]
    print("PASS: Validation error on invalid name characters returns 422")
    passed += 1

    # 12. Validation error: Invalid Phone length
    bad_payload = new_patient.copy()
    bad_payload["phone_number"] = "12345"
    res = client.post("/patients", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["data"] is None
    assert "phone_number" in res.json()["error"]
    print("PASS: Validation error on invalid phone length returns 422")
    passed += 1

    # 13. Validation error: Invalid Sex enum
    bad_payload = new_patient.copy()
    bad_payload["sex"] = "Unknown"
    res = client.post("/patients", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["data"] is None
    assert "sex" in res.json()["error"]
    print("PASS: Validation error on invalid sex enum returns 422")
    passed += 1

    print("=" * 60)
    print(f"ALL {passed} IN-PROCESS TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
