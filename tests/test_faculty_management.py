import pytest
from app.models.faculty import Faculty

def seed_faculty_data(db_session):
    fac1 = Faculty(
        id="fac-science-001",
        code="FSC",
        name="Faculty of Science",
        description="Faculty of Science Department"
    )
    fac2 = Faculty(
        id="fac-medicine-002",
        code="FMD",
        name="Faculty of Medicine",
        description="Faculty of Medicine Department"
    )
    db_session.add_all([fac1, fac2])
    db_session.commit()

def test_create_faculty_success(client, db_session):
    payload = {
        "code": "FENG",
        "name": "Faculty of Engineering",
        "description": "Faculty of Engineering and Technology"
    }
    response = client.post("/faculties", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "FENG"
    assert data["data"]["name"] == "Faculty of Engineering"
    assert data["data"]["description"] == "Faculty of Engineering and Technology"
    assert "id" in data["data"]

    # Verify directly in DB
    db_fac = db_session.query(Faculty).filter(Faculty.code == "FENG").first()
    assert db_fac is not None
    assert db_fac.name == "Faculty of Engineering"

def test_create_faculty_duplicate_code_rejected(client, db_session):
    seed_faculty_data(db_session)
    payload = {
        "code": "FSC",  # Duplicate code
        "name": "Another Faculty of Science",
        "description": "Duplicate faculty code attempt"
    }
    response = client.post("/faculties", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_CODE_ALREADY_EXISTS"

def test_create_faculty_malformed_code_rejected(client, db_session):
    payload = {
        "code": "F",  # Too short (min length 2)
        "name": "Faculty of Invalid Code",
        "description": "Invalid format attempt"
    }
    response = client.post("/faculties", json=payload)
    assert response.status_code in [400, 422]

def test_list_faculties(client, db_session):
    seed_faculty_data(db_session)
    response = client.get("/faculties")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 2
    codes = [f["code"] for f in data["data"]]
    assert "FSC" in codes
    assert "FMD" in codes

def test_get_faculty_by_id_success(client, db_session):
    seed_faculty_data(db_session)
    response = client.get("/faculties/fac-science-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "fac-science-001"
    assert data["data"]["code"] == "FSC"

def test_get_faculty_by_code_success(client, db_session):
    seed_faculty_data(db_session)
    response = client.get("/faculties/FMD")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "fac-medicine-002"
    assert data["data"]["code"] == "FMD"

def test_get_faculty_nonexistent_rejected(client, db_session):
    seed_faculty_data(db_session)
    response = client.get("/faculties/non-existent-faculty")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_NOT_FOUND"

def test_update_faculty_success(client, db_session):
    seed_faculty_data(db_session)
    update_payload = {
        "name": "Faculty of Pure and Applied Science",
        "description": "Updated science faculty description"
    }
    response = client.put("/faculties/fac-science-001", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Faculty of Pure and Applied Science"
    assert data["data"]["description"] == "Updated science faculty description"
    assert data["data"]["code"] == "FSC"

    # Verify directly in DB
    db_fac = db_session.query(Faculty).filter(Faculty.id == "fac-science-001").first()
    assert db_fac.name == "Faculty of Pure and Applied Science"

def test_update_faculty_duplicate_code_rejected(client, db_session):
    seed_faculty_data(db_session)
    # Attempt to change fac-science-001 code to FMD (which is already held by fac-medicine-002)
    update_payload = {
        "code": "FMD"
    }
    response = client.put("/faculties/fac-science-001", json=update_payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_CODE_ALREADY_EXISTS"

def test_delete_faculty_success(client, db_session):
    seed_faculty_data(db_session)
    response = client.delete("/faculties/fac-science-001")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Subsequent GET returns 404
    get_res = client.get("/faculties/fac-science-001")
    assert get_res.status_code == 404

    # Verify directly in DB
    db_fac = db_session.query(Faculty).filter(Faculty.id == "fac-science-001").first()
    assert db_fac is None

def test_delete_nonexistent_faculty_rejected(client, db_session):
    seed_faculty_data(db_session)
    response = client.delete("/faculties/non-existent-faculty")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FACULTY_NOT_FOUND"

def test_faculty_crud_integration_with_validation_endpoint(client, db_session):
    """
    End-to-End Integration Flow:
    1. Create faculty via POST /faculties -> 201 Created.
    2. Call Daya's GET /validation/faculties/{code} -> 200 OK with is_valid=True.
    3. Update faculty via PUT /faculties/{id} -> 200 OK.
    4. Call validation endpoint again -> 200 OK with updated name.
    5. Delete faculty via DELETE /faculties/{id} -> 200 OK.
    6. Call validation endpoint again -> 404 NOT_FOUND.
    """
    # 1. Create faculty
    create_payload = {
        "code": "FHUM",
        "name": "Faculty of Humanities",
        "description": "Faculty of Humanities Department"
    }
    create_res = client.post("/faculties", json=create_payload)
    assert create_res.status_code == 201
    fac_id = create_res.json()["data"]["id"]

    # 2. Validate via Daya's endpoint
    val_res1 = client.get("/validation/faculties/FHUM")
    assert val_res1.status_code == 200
    assert val_res1.json()["data"]["faculty_id"] == fac_id
    assert val_res1.json()["data"]["code"] == "FHUM"
    assert val_res1.json()["data"]["is_valid"] is True

    # 3. Update faculty
    update_res = client.put(f"/faculties/{fac_id}", json={"name": "Faculty of Social Sciences & Humanities"})
    assert update_res.status_code == 200

    # 4. Re-validate via Daya's endpoint
    val_res2 = client.get("/validation/faculties/FHUM")
    assert val_res2.status_code == 200
    assert val_res2.json()["data"]["name"] == "Faculty of Social Sciences & Humanities"

    # 5. Delete faculty
    del_res = client.delete(f"/faculties/{fac_id}")
    assert del_res.status_code == 200

    # 6. Validate via Daya's endpoint -> now 404
    val_res3 = client.get("/validation/faculties/FHUM")
    assert val_res3.status_code == 404
    assert val_res3.json()["error"]["code"] == "FACULTY_NOT_FOUND"
