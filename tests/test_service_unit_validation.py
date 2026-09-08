import pytest
from app.models.service_unit import ServiceUnit

def seed_service_unit_data(db_session):
    unit1 = ServiceUnit(
        id="unit-it-201",
        code="UNIT-IT",
        name="IT Services Unit",
        description="Central IT Support Services"
    )
    unit2 = ServiceUnit(
        id="unit-lib-202",
        code="UNIT-LIB",
        name="Library Services Unit",
        description="University Library & Learning Resources"
    )
    db_session.add_all([unit1, unit2])
    db_session.commit()

def test_validate_service_unit_by_id(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/validation/service-units/unit-it-201")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["unit_id"] == "unit-it-201"
    assert data["data"]["code"] == "UNIT-IT"
    assert data["data"]["name"] == "IT Services Unit"
    assert data["data"]["description"] == "Central IT Support Services"
    assert data["data"]["is_valid"] is True

def test_validate_service_unit_by_code(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/validation/service-units/UNIT-LIB")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["unit_id"] == "unit-lib-202"
    assert data["data"]["code"] == "UNIT-LIB"

def test_validate_unknown_service_unit(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/validation/service-units/non-existent-unit")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNIT_NOT_FOUND"

def test_validate_malformed_service_unit_id(client, db_session):
    seed_service_unit_data(db_session)
    response = client.get("/validation/service-units/a")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_IDENTIFIER_FORMAT"
