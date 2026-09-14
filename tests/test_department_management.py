import pytest
from app.models.faculty import Faculty
from app.models.department import Department

def seed_faculty_and_departments(db_session):
    fac1 = Faculty(
        id="fac-comp-001",
        code="FC",
        name="Faculty of Computing",
        description="Computing & IT Faculty"
    )
    fac2 = Faculty(
        id="fac-science-002",
        code="FSC",
        name="Faculty of Science",
        description="Faculty of Science"
    )
    db_session.add_all([fac1, fac2])
    db_session.commit()

    dept1 = Department(
        id="dept-cs-101",
        code="DEPT-CS",
        name="Department of Computer Science",
        faculty_id="fac-comp-001"
    )
    dept2 = Department(
        id="dept-se-102",
        code="DEPT-SE",
        name="Department of Software Engineering",
        faculty_id="fac-comp-001"
    )
    db_session.add_all([dept1, dept2])
    db_session.commit()

# --- Creation Tests ---

def test_create_department_success(client, db_session):
    seed_faculty_and_departments(db_session)
    payload = {
        "code": "DEPT-IS",
        "name": "Department of Information Systems",
        "faculty_id": "fac-comp-001"
    }
    response = client.post("/departments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "DEPT-IS"
    assert data["data"]["name"] == "Department of Information Systems"
    assert data["data"]["faculty_id"] == "fac-comp-001"
    assert "id" in data["data"]
    assert data["data"]["id"].startswith("dept-dept-is-")

    # Verify directly in DB
    db_dept = db_session.query(Department).filter(Department.code == "DEPT-IS").first()
    assert db_dept is not None
    assert db_dept.name == "Department of Information Systems"
    assert db_dept.faculty_id == "fac-comp-001"

def test_create_department_with_faculty_code(client, db_session):
    seed_faculty_and_departments(db_session)
    payload = {
        "code": "DEPT-CHEM",
        "name": "Department of Chemistry",
        "faculty_id": "FSC"  # Referenced by Faculty code
    }
    response = client.post("/departments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "DEPT-CHEM"
    assert data["data"]["faculty_id"] == "fac-science-002"

def test_create_department_duplicate_code_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    payload = {
        "code": "DEPT-CS",  # Duplicate code
        "name": "Another Computer Science Dept",
        "faculty_id": "fac-comp-001"
    }
    response = client.post("/departments", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DEPARTMENT_CODE_ALREADY_EXISTS"

def test_create_department_nonexistent_faculty_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    payload = {
        "code": "DEPT-BIO",
        "name": "Department of Biology",
        "faculty_id": "non-existent-faculty-id"
    }
    response = client.post("/departments", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_NOT_FOUND"

def test_create_department_malformed_code_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    payload = {
        "code": "D",  # Too short (min length 2)
        "name": "Invalid Department",
        "faculty_id": "fac-comp-001"
    }
    response = client.post("/departments", json=payload)
    assert response.status_code in [400, 422]

# --- Retrieval Tests ---

def test_list_departments(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 2
    codes = [d["code"] for d in data["data"]]
    assert "DEPT-CS" in codes
    assert "DEPT-SE" in codes

def test_list_departments_pagination(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1

def test_list_departments_filter_by_faculty(client, db_session):
    seed_faculty_and_departments(db_session)
    # Add a department in fac2
    dept_sci = Department(
        id="dept-math-201",
        code="DEPT-MATH",
        name="Department of Mathematics",
        faculty_id="fac-science-002"
    )
    db_session.add(dept_sci)
    db_session.commit()

    # Filter by fac-science-002
    response = client.get("/departments?faculty_id=fac-science-002")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["code"] == "DEPT-MATH"

def test_get_department_by_id_success(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments/dept-cs-101")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "dept-cs-101"
    assert data["data"]["code"] == "DEPT-CS"
    assert data["data"]["name"] == "Department of Computer Science"

def test_get_department_by_code_success(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments/dept-se")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "dept-se-102"
    assert data["data"]["code"] == "DEPT-SE"

def test_get_department_nonexistent_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments/non-existent-dept")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DEPARTMENT_NOT_FOUND"

def test_get_department_malformed_identifier_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.get("/departments/x")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"

# --- Update Tests ---

def test_update_department_name_success(client, db_session):
    seed_faculty_and_departments(db_session)
    update_payload = {
        "name": "Department of Computer Science and Engineering"
    }
    response = client.put("/departments/dept-cs-101", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Department of Computer Science and Engineering"
    assert data["data"]["code"] == "DEPT-CS"

    # Verify directly in DB
    db_dept = db_session.query(Department).filter(Department.id == "dept-cs-101").first()
    assert db_dept.name == "Department of Computer Science and Engineering"

def test_patch_department_code_success(client, db_session):
    seed_faculty_and_departments(db_session)
    patch_payload = {
        "code": "DEPT-CS-NEW"
    }
    response = client.patch("/departments/dept-cs-101", json=patch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "DEPT-CS-NEW"

    # Verify directly in DB
    db_dept = db_session.query(Department).filter(Department.id == "dept-cs-101").first()
    assert db_dept.code == "DEPT-CS-NEW"

def test_update_department_faculty_reassignment(client, db_session):
    seed_faculty_and_departments(db_session)
    update_payload = {
        "faculty_id": "fac-science-002"
    }
    response = client.put("/departments/dept-cs-101", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["faculty_id"] == "fac-science-002"

    # Verify in DB
    db_dept = db_session.query(Department).filter(Department.id == "dept-cs-101").first()
    assert db_dept.faculty_id == "fac-science-002"

def test_update_department_nonexistent_faculty_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    update_payload = {
        "faculty_id": "non-existent-faculty"
    }
    response = client.put("/departments/dept-cs-101", json=update_payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_NOT_FOUND"

def test_update_department_duplicate_code_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    # Attempt to change dept-cs-101 code to DEPT-SE (held by dept-se-102)
    update_payload = {
        "code": "DEPT-SE"
    }
    response = client.put("/departments/dept-cs-101", json=update_payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DEPARTMENT_CODE_ALREADY_EXISTS"

# --- Deletion Tests ---

def test_delete_department_success(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.delete("/departments/dept-cs-101")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Subsequent GET returns 404
    get_res = client.get("/departments/dept-cs-101")
    assert get_res.status_code == 404

    # Verify directly in DB
    db_dept = db_session.query(Department).filter(Department.id == "dept-cs-101").first()
    assert db_dept is None

def test_delete_nonexistent_department_rejected(client, db_session):
    seed_faculty_and_departments(db_session)
    response = client.delete("/departments/non-existent-dept")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEPARTMENT_NOT_FOUND"

# --- Integration Tests with USM-108 Validation ---

def test_department_crud_integration_with_validation_endpoint(client, db_session):
    """
    End-to-End Integration Flow:
    1. Seed faculty FC.
    2. Create department via POST /departments -> 201 Created.
    3. Call Daya's GET /validation/departments/{code} -> 200 OK with is_valid=True.
    4. Update department via PUT /departments/{id} -> 200 OK.
    5. Call validation endpoint again -> 200 OK with updated name.
    6. Delete department via DELETE /departments/{id} -> 200 OK.
    7. Call validation endpoint again -> 404 NOT_FOUND.
    """
    fac = Faculty(
        id="fac-arts-003",
        code="FARTS",
        name="Faculty of Arts",
        description="Faculty of Arts & Design"
    )
    db_session.add(fac)
    db_session.commit()

    # 1. Create department
    create_payload = {
        "code": "DEPT-HIST",
        "name": "Department of History",
        "faculty_id": "fac-arts-003"
    }
    create_res = client.post("/departments", json=create_payload)
    assert create_res.status_code == 201
    dept_id = create_res.json()["data"]["id"]

    # 2. Validate via Daya's validation endpoint
    val_res1 = client.get("/validation/departments/DEPT-HIST")
    assert val_res1.status_code == 200
    val_data1 = val_res1.json()["data"]
    assert val_data1["department_id"] == dept_id
    assert val_data1["code"] == "DEPT-HIST"
    assert val_data1["name"] == "Department of History"
    assert val_data1["faculty_id"] == "fac-arts-003"
    assert val_data1["faculty_name"] == "Faculty of Arts"
    assert val_data1["is_valid"] is True

    # 3. Update department
    update_res = client.put(f"/departments/{dept_id}", json={"name": "Department of History & Archaeology"})
    assert update_res.status_code == 200

    # 4. Re-validate via Daya's endpoint
    val_res2 = client.get("/validation/departments/DEPT-HIST")
    assert val_res2.status_code == 200
    assert val_res2.json()["data"]["name"] == "Department of History & Archaeology"

    # 5. Delete department
    del_res = client.delete(f"/departments/{dept_id}")
    assert del_res.status_code == 200

    # 6. Validate via Daya's endpoint -> now 404
    val_res3 = client.get("/validation/departments/DEPT-HIST")
    assert val_res3.status_code == 404
    assert val_res3.json()["error"]["code"] == "DEPARTMENT_NOT_FOUND"
