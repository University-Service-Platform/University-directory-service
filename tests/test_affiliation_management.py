import pytest
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.user_affiliation import UserAffiliation

def seed_affiliation_base_data(db_session):
    fac1 = Faculty(
        id="fac-comp-101",
        code="FC",
        name="Faculty of Computing",
        description="Computing & IT Faculty"
    )
    fac2 = Faculty(
        id="fac-science-102",
        code="FSC",
        name="Faculty of Science",
        description="Faculty of Pure Science"
    )
    db_session.add_all([fac1, fac2])
    db_session.commit()

    dept1 = Department(
        id="dept-cs-101",
        code="DEPT-CS",
        name="Department of Computer Science",
        faculty_id="fac-comp-101"
    )
    dept2 = Department(
        id="dept-chem-102",
        code="DEPT-CHEM",
        name="Department of Chemistry",
        faculty_id="fac-science-102"
    )
    dept3 = Department(
        id="dept-se-103",
        code="DEPT-SE",
        name="Department of Software Engineering",
        faculty_id="fac-comp-101"
    )
    db_session.add_all([dept1, dept2, dept3])
    db_session.commit()

# ==============================================================================
# CREATION TESTS
# ==============================================================================

def test_create_affiliation_success(client, db_session):
    """1. Successful affiliation creation with explicit valid faculty."""
    seed_affiliation_base_data(db_session)
    payload = {
        "user_id": "usr-student-001",
        "department_id": "dept-cs-101",
        "faculty_id": "fac-comp-101"
    }
    response = client.post("/affiliations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "usr-student-001"
    assert data["data"]["department_id"] == "dept-cs-101"
    assert data["data"]["department_name"] == "Department of Computer Science"
    assert data["data"]["faculty_id"] == "fac-comp-101"
    assert data["data"]["faculty_name"] == "Faculty of Computing"
    assert "id" in data["data"]
    assert data["data"]["id"].startswith("aff-usr-student-001-")

    # Verify directly in DB
    db_aff = db_session.query(UserAffiliation).filter(UserAffiliation.user_id == "usr-student-001").first()
    assert db_aff is not None
    assert db_aff.department_id == "dept-cs-101"
    assert db_aff.faculty_id == "fac-comp-101"

def test_create_affiliation_faculty_automatically_derived(client, db_session):
    """2. Faculty automatically derived from department when omitted."""
    seed_affiliation_base_data(db_session)
    payload = {
        "user_id": "usr-student-002",
        "department_id": "dept-chem-102"
        # faculty_id omitted
    }
    response = client.post("/affiliations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "usr-student-002"
    assert data["data"]["department_id"] == "dept-chem-102"
    assert data["data"]["faculty_id"] == "fac-science-102"
    assert data["data"]["faculty_name"] == "Faculty of Science"

def test_create_affiliation_nonexistent_department_rejected(client, db_session):
    """3. Nonexistent department rejected with 404 DEPARTMENT_NOT_FOUND."""
    seed_affiliation_base_data(db_session)
    payload = {
        "user_id": "usr-student-003",
        "department_id": "non-existent-dept"
    }
    response = client.post("/affiliations", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DEPARTMENT_NOT_FOUND"

def test_create_affiliation_nonexistent_faculty_rejected(client, db_session):
    """4. Nonexistent faculty rejected with 404 FACULTY_NOT_FOUND."""
    seed_affiliation_base_data(db_session)
    payload = {
        "user_id": "usr-student-004",
        "department_id": "dept-cs-101",
        "faculty_id": "non-existent-faculty"
    }
    response = client.post("/affiliations", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_NOT_FOUND"

def test_create_affiliation_mismatched_department_faculty_rejected(client, db_session):
    """5. Mismatched department/faculty rejected with 400 INVALID_ORGANIZATIONAL_RELATIONSHIP."""
    seed_affiliation_base_data(db_session)
    # dept-cs-101 belongs to fac-comp-101, but payload specifies fac-science-102
    payload = {
        "user_id": "usr-student-005",
        "department_id": "dept-cs-101",
        "faculty_id": "fac-science-102"
    }
    response = client.post("/affiliations", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_ORGANIZATIONAL_RELATIONSHIP"

def test_create_affiliation_duplicate_rejected(client, db_session):
    """6. Duplicate affiliation for same user and department rejected with 409 AFFILIATION_ALREADY_EXISTS."""
    seed_affiliation_base_data(db_session)
    payload = {
        "user_id": "usr-student-006",
        "department_id": "dept-cs-101"
    }
    res1 = client.post("/affiliations", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/affiliations", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AFFILIATION_ALREADY_EXISTS"

# ==============================================================================
# RETRIEVAL TESTS
# ==============================================================================

def test_get_user_affiliation_success(client, db_session):
    """7. Get user organizational affiliation successfully."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-test-001",
        user_id="usr-staff-101",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    response = client.get("/affiliations/users/usr-staff-101")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "usr-staff-101"
    assert data["data"]["department_id"] == "dept-cs-101"
    assert data["data"]["department_name"] == "Department of Computer Science"
    assert data["data"]["faculty_id"] == "fac-comp-101"
    assert data["data"]["faculty_name"] == "Faculty of Computing"

def test_get_nonexistent_user_affiliation_rejected(client, db_session):
    """8. Get nonexistent user affiliation returns 404 AFFILIATION_NOT_FOUND."""
    seed_affiliation_base_data(db_session)
    response = client.get("/affiliations/users/non-existent-user")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AFFILIATION_NOT_FOUND"

def test_get_affiliation_by_id(client, db_session):
    """9. Get affiliation by unique affiliation ID."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-id-001",
        user_id="usr-student-007",
        department_id="dept-chem-102",
        faculty_id="fac-science-102"
    )
    db_session.add(aff)
    db_session.commit()

    response = client.get("/affiliations/aff-id-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "aff-id-001"
    assert data["data"]["department_id"] == "dept-chem-102"

def test_list_affiliations(client, db_session):
    """10. List affiliations."""
    seed_affiliation_base_data(db_session)
    aff1 = UserAffiliation(id="aff-l-1", user_id="u-1", department_id="dept-cs-101", faculty_id="fac-comp-101")
    aff2 = UserAffiliation(id="aff-l-2", user_id="u-2", department_id="dept-chem-102", faculty_id="fac-science-102")
    db_session.add_all([aff1, aff2])
    db_session.commit()

    response = client.get("/affiliations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 2

def test_list_affiliations_filter_by_department(client, db_session):
    """11. Filter affiliations by department_id."""
    seed_affiliation_base_data(db_session)
    aff1 = UserAffiliation(id="aff-d-1", user_id="u-1", department_id="dept-cs-101", faculty_id="fac-comp-101")
    aff2 = UserAffiliation(id="aff-d-2", user_id="u-2", department_id="dept-chem-102", faculty_id="fac-science-102")
    db_session.add_all([aff1, aff2])
    db_session.commit()

    response = client.get("/affiliations?department_id=dept-cs-101")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["user_id"] == "u-1"

def test_list_affiliations_filter_by_faculty(client, db_session):
    """12. Filter affiliations by faculty_id."""
    seed_affiliation_base_data(db_session)
    aff1 = UserAffiliation(id="aff-f-1", user_id="u-1", department_id="dept-cs-101", faculty_id="fac-comp-101")
    aff2 = UserAffiliation(id="aff-f-2", user_id="u-2", department_id="dept-chem-102", faculty_id="fac-science-102")
    db_session.add_all([aff1, aff2])
    db_session.commit()

    response = client.get("/affiliations?faculty_id=fac-science-102")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["user_id"] == "u-2"

def test_list_affiliations_filter_by_user(client, db_session):
    """13. Filter affiliations by user_id."""
    seed_affiliation_base_data(db_session)
    aff1 = UserAffiliation(id="aff-u-1", user_id="u-specific", department_id="dept-cs-101", faculty_id="fac-comp-101")
    aff2 = UserAffiliation(id="aff-u-2", user_id="u-other", department_id="dept-chem-102", faculty_id="fac-science-102")
    db_session.add_all([aff1, aff2])
    db_session.commit()

    response = client.get("/affiliations?user_id=u-specific")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "aff-u-1"

# ==============================================================================
# UPDATE TESTS
# ==============================================================================

def test_update_department_successfully(client, db_session):
    """14. Update department successfully within the same faculty."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-up-1",
        user_id="usr-student-008",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    # Change to dept-se-103 (same faculty fac-comp-101)
    response = client.put("/affiliations/aff-up-1", json={"department_id": "dept-se-103"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["department_id"] == "dept-se-103"
    assert data["data"]["faculty_id"] == "fac-comp-101"

    # Verify directly in DB
    db_aff = db_session.query(UserAffiliation).filter(UserAffiliation.id == "aff-up-1").first()
    assert db_aff.department_id == "dept-se-103"

def test_transfer_user_department_and_synchronize_faculty(client, db_session):
    """15. Transfer user to another department across faculties and synchronize faculty."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-up-2",
        user_id="usr-student-009",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    # Transfer to Chemistry in Faculty of Science
    response = client.put("/affiliations/aff-up-2", json={"department_id": "dept-chem-102"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["department_id"] == "dept-chem-102"
    assert data["data"]["faculty_id"] == "fac-science-102"

    # Verify directly in DB
    db_aff = db_session.query(UserAffiliation).filter(UserAffiliation.id == "aff-up-2").first()
    assert db_aff.department_id == "dept-chem-102"
    assert db_aff.faculty_id == "fac-science-102"

def test_invalid_department_during_update_rejected(client, db_session):
    """16. Invalid department during update rejected."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-up-3",
        user_id="usr-student-010",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    response = client.put("/affiliations/aff-up-3", json={"department_id": "non-existent-dept"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEPARTMENT_NOT_FOUND"

def test_invalid_department_faculty_combination_during_update_rejected(client, db_session):
    """17. Invalid department/faculty combination during update rejected."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-up-4",
        user_id="usr-student-011",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    # dept-chem-102 belongs to fac-science-102, but payload claims fac-comp-101
    response = client.put("/affiliations/aff-up-4", json={
        "department_id": "dept-chem-102",
        "faculty_id": "fac-comp-101"
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ORGANIZATIONAL_RELATIONSHIP"

# ==============================================================================
# DELETION TESTS
# ==============================================================================

def test_delete_affiliation_success(client, db_session):
    """18. Delete affiliation successfully."""
    seed_affiliation_base_data(db_session)
    aff = UserAffiliation(
        id="aff-del-1",
        user_id="usr-student-012",
        department_id="dept-cs-101",
        faculty_id="fac-comp-101"
    )
    db_session.add(aff)
    db_session.commit()

    response = client.delete("/affiliations/aff-del-1")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # 19. Deleted affiliation cannot be retrieved
    get_res = client.get("/affiliations/aff-del-1")
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "AFFILIATION_NOT_FOUND"

    # Verify directly in DB
    db_aff = db_session.query(UserAffiliation).filter(UserAffiliation.id == "aff-del-1").first()
    assert db_aff is None

# ==============================================================================
# CASCADE & INTEGRATION TESTS
# ==============================================================================

def test_department_deletion_cascades_affiliations(client, db_session):
    """
    20. Create department + affiliation.
    21. Delete department through the existing USM-107 functionality.
    22. Verify the affiliation is removed through the department cascade.
    """
    seed_affiliation_base_data(db_session)

    # 20. Create department + affiliation
    dept_res = client.post("/departments", json={
        "code": "DEPT-PHYS",
        "name": "Department of Physics",
        "faculty_id": "fac-science-102"
    })
    assert dept_res.status_code == 201
    dept_id = dept_res.json()["data"]["id"]

    aff_res = client.post("/affiliations", json={
        "user_id": "usr-phys-student",
        "department_id": dept_id
    })
    assert aff_res.status_code == 201
    aff_id = aff_res.json()["data"]["id"]

    # Verify affiliation exists
    get_aff1 = client.get(f"/affiliations/{aff_id}")
    assert get_aff1.status_code == 200

    # 21. Delete department through USM-107 API
    del_dept = client.delete(f"/departments/{dept_id}")
    assert del_dept.status_code == 200

    # 22. Verify the affiliation is removed through cascade
    get_aff2 = client.get(f"/affiliations/{aff_id}")
    assert get_aff2.status_code == 404
    assert get_aff2.json()["error"]["code"] == "AFFILIATION_NOT_FOUND"

    # Direct DB verification
    db_aff = db_session.query(UserAffiliation).filter(UserAffiliation.id == aff_id).first()
    assert db_aff is None
