import pytest
from app.models.service_unit import ServiceUnit
from app.models.faculty import Faculty

def seed_service_unit_data(db_session):
    u1 = ServiceUnit(
        id="unit-lib-001",
        code="LIB",
        name="Main University Library",
        description="Central academic library"
    )
    u2 = ServiceUnit(
        id="unit-its-002",
        code="ITS",
        name="Information Technology Services",
        description="University IT infrastructure and support"
    )
    db_session.add_all([u1, u2])
    db_session.commit()

def test_create_service_unit_success(client, db_session):
    payload = {
        "code": "HC",
        "name": "Health Centre",
        "description": "Campus healthcare services"
    }
    response = client.post("/service-units", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["code"] == "HC"
    assert data["data"]["name"] == "Health Centre"
    assert data["data"]["description"] == "Campus healthcare services"
    assert "id" in data["data"]

    # Verify directly in DB
    db_unit = db_session.query(ServiceUnit).filter(ServiceUnit.code == "HC").first()
    assert db_unit is not None
    assert db_unit.name == "Health Centre"

def test_create_service_unit_duplicate_code_rejected(client, db_session):
    seed_service_unit_data(db_session)
    payload = {
        "code": "LIB",  # Duplicate code
        "name": "Another Library",
        "description": "Duplicate service unit code attempt"
    }
    response = client.post("/service-units", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_CODE_ALREADY_EXISTS"

def test_create_service_unit_malformed_code_rejected(client, db_session):
    payload = {
        "code": "L",  # Too short (min length 2)
        "name": "Invalid Service Unit",
        "description": "Malformed code attempt"
    }
    response = client.post("/service-units", json=payload)
    assert response.status_code in [400, 422]

def test_list_service_units(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/service-units")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 2
    codes = [u["code"] for u in data["data"]]
    assert "LIB" in codes
    assert "ITS" in codes

def test_list_service_units_pagination(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/service-units?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1

def test_get_service_unit_by_id(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/service-units/unit-lib-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "unit-lib-001"
    assert data["data"]["code"] == "LIB"
    assert data["data"]["name"] == "Main University Library"

def test_get_service_unit_by_code(client, db_session):
    seed_service_unit_data(db_session)
    # Testing case normalization
    response = client.get("/service-units/its")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "unit-its-002"
    assert data["data"]["code"] == "ITS"

def test_get_service_unit_not_found(client, db_session):
    response = client.get("/service-units/NONEXISTENT")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_NOT_FOUND"

def test_get_service_unit_invalid_identifier_format(client, db_session):
    response = client.get("/service-units/*invalid*id!")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"

def test_update_service_unit_success(client, db_session):
    seed_service_unit_data(db_session)
    payload = {
        "name": "Updated University Library",
        "description": "Expanded university central library",
        "code": "ULIB"
    }
    response = client.put("/service-units/unit-lib-001", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Updated University Library"
    assert data["data"]["code"] == "ULIB"
    assert data["data"]["description"] == "Expanded university central library"

    # Verify persistence
    db_unit = db_session.query(ServiceUnit).filter(ServiceUnit.id == "unit-lib-001").first()
    assert db_unit.code == "ULIB"
    assert db_unit.name == "Updated University Library"

def test_update_service_unit_duplicate_code_rejected(client, db_session):
    seed_service_unit_data(db_session)
    payload = {
        "code": "ITS"  # already taken by unit-its-002
    }
    response = client.put("/service-units/unit-lib-001", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_CODE_ALREADY_EXISTS"

def test_update_service_unit_not_found(client, db_session):
    payload = {"name": "Nonexistent Unit"}
    response = client.put("/service-units/NONEXISTENT", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_NOT_FOUND"

def test_delete_service_unit_success(client, db_session):
    seed_service_unit_data(db_session)
    response = client.delete("/service-units/unit-lib-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "was successfully deleted" in data["data"]["message"]

    # Verify deleted from DB
    db_unit = db_session.query(ServiceUnit).filter(ServiceUnit.id == "unit-lib-001").first()
    assert db_unit is None

def test_delete_service_unit_not_found(client, db_session):
    response = client.delete("/service-units/NONEXISTENT")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_NOT_FOUND"

def test_service_unit_crud_independence_from_faculties(client, db_session):
    # Seed a faculty
    fac = Faculty(
        id="fac-science-001",
        code="FSC",
        name="Faculty of Science",
        description="Science Faculty"
    )
    db_session.add(fac)
    db_session.commit()

    # Create a service unit
    payload = {
        "code": "FIN",
        "name": "Finance Department / Office",
        "description": "Central Financial Services"
    }
    res_unit = client.post("/service-units", json=payload)
    assert res_unit.status_code == 201

    # Ensure faculty remains intact
    fac_db = db_session.query(Faculty).filter(Faculty.id == "fac-science-001").first()
    assert fac_db is not None
    assert fac_db.code == "FSC"

    # Ensure faculty validation endpoint still works independently
    res_val = client.get("/validation/faculties/FSC")
    assert res_val.status_code == 200
    assert res_val.json()["data"]["code"] == "FSC"
