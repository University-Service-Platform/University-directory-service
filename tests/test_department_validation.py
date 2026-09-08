import pytest
from app.models.faculty import Faculty
from app.models.department import Department

def seed_department_data(db_session):
    faculty = Faculty(
        id="fac-comp-001",
        code="FC",
        name="Faculty of Computing",
        description="Computing & IT Faculty"
    )
    db_session.add(faculty)
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

def test_validate_department_by_id(client, db_session):
    seed_department_data(db_session)
    response = client.get("/validation/departments/dept-cs-101")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["department_id"] == "dept-cs-101"
    assert data["data"]["code"] == "DEPT-CS"
    assert data["data"]["name"] == "Department of Computer Science"
    assert data["data"]["faculty_id"] == "fac-comp-001"
    assert data["data"]["faculty_name"] == "Faculty of Computing"
    assert data["data"]["is_valid"] is True

def test_validate_department_by_code(client, db_session):
    seed_department_data(db_session)
    response = client.get("/validation/departments/DEPT-SE")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["department_id"] == "dept-se-102"
    assert data["data"]["code"] == "DEPT-SE"

def test_validate_unknown_department(client, db_session):
    seed_department_data(db_session)
    response = client.get("/validation/departments/non-existent-dept")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DEPARTMENT_NOT_FOUND"

def test_validate_malformed_department_id(client, db_session):
    seed_department_data(db_session)
    response = client.get("/validation/departments/a")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"
