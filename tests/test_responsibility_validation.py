import pytest
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.service_unit import ServiceUnit
from app.models.service_responsibility import ServiceResponsibility, ResponsibilityStatus

def seed_responsibility_data(db_session):
    faculty = Faculty(
        id="fac-science-301",
        code="FS",
        name="Faculty of Science"
    )
    dept = Department(
        id="dept-chem-301",
        code="DEPT-CHEM",
        name="Department of Chemistry",
        faculty_id="fac-science-301"
    )
    unit = ServiceUnit(
        id="unit-lab-301",
        code="UNIT-LAB",
        name="Chemistry Lab Support Unit"
    )
    db_session.add_all([faculty, dept, unit])
    db_session.commit()

    # Seed ACTIVE responsibility relationship for user 'usr-staff-301'
    resp_active = ServiceResponsibility(
        id="resp-301",
        user_id="usr-staff-301",
        service_unit_id="unit-lab-301",
        department_id="dept-chem-301",
        faculty_id="fac-science-301",
        role_title="Lab Coordinator",
        status=ResponsibilityStatus.ACTIVE
    )
    # Seed INACTIVE responsibility relationship for user 'usr-staff-302'
    resp_inactive = ServiceResponsibility(
        id="resp-302",
        user_id="usr-staff-302",
        service_unit_id="unit-lab-301",
        role_title="Former Tech Officer",
        status=ResponsibilityStatus.INACTIVE
    )
    db_session.add_all([resp_active, resp_inactive])
    db_session.commit()

def test_validate_actual_responsibility_relationship_success(client, db_session):
    seed_responsibility_data(db_session)
    response = client.get("/validation/users/usr-staff-301/responsibilities")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "usr-staff-301"
    assert data["data"]["is_valid"] is True
    assert len(data["data"]["responsibilities"]) == 1
    
    r = data["data"]["responsibilities"][0]
    assert r["responsibility_id"] == "resp-301"
    assert r["role_title"] == "Lab Coordinator"
    assert r["service_unit_name"] == "Chemistry Lab Support Unit"
    assert r["department_name"] == "Department of Chemistry"
    assert r["faculty_name"] == "Faculty of Science"

def test_missing_actual_relationship_rejected(client, db_session):
    """
    Prompt Section 20 requirement:
    Verify that merely having records exist independently does NOT grant valid responsibility.
    User 'usr-staff-999' does NOT have a ServiceResponsibility record.
    """
    seed_responsibility_data(db_session)
    response = client.get("/validation/users/usr-staff-999/responsibilities")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESPONSIBILITY_NOT_FOUND"

def test_inactive_responsibility_relationship_denied(client, db_session):
    seed_responsibility_data(db_session)
    response = client.get("/validation/users/usr-staff-302/responsibilities")
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESPONSIBILITY_INACTIVE"

def test_unknown_user_responsibility_rejected(client, db_session):
    seed_responsibility_data(db_session)
    response = client.get("/validation/users/non-existent-user/responsibilities")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESPONSIBILITY_NOT_FOUND"

def test_malformed_user_identifier_rejected(client, db_session):
    seed_responsibility_data(db_session)
    response = client.get("/validation/users/a/responsibilities")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"
