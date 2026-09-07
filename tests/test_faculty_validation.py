import pytest
from app.models.faculty import Faculty

def seed_faculties(db_session):
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

def test_directory_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_validate_faculty_by_id(client, db_session):
    seed_faculties(db_session)
    response = client.get("/validation/faculties/fac-science-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["faculty_id"] == "fac-science-001"
    assert data["data"]["code"] == "FSC"
    assert data["data"]["name"] == "Faculty of Science"
    assert data["data"]["is_valid"] is True

def test_validate_faculty_by_code(client, db_session):
    seed_faculties(db_session)
    response = client.get("/validation/faculties/FMD")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["faculty_id"] == "fac-medicine-002"
    assert data["data"]["code"] == "FMD"

def test_validate_unknown_faculty(client, db_session):
    seed_faculties(db_session)
    response = client.get("/validation/faculties/non-existent-fac")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FACULTY_NOT_FOUND"

def test_validate_malformed_faculty_id(client, db_session):
    seed_faculties(db_session)
    response = client.get("/validation/faculties/a")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"
