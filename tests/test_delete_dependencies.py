"""Deleting directory entities that still have dependent records returns 409 (no cascade)."""
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_responsibility import ResponsibilityStatus, ServiceResponsibility
from app.models.service_unit import ServiceUnit
from app.models.user_affiliation import UserAffiliation


def seed(db_session):
    # Synthetic test data.
    db_session.add_all([
        Faculty(id="fac-syn-001", code="FSYN", name="Synthetic Faculty"),
        Faculty(id="fac-empty-002", code="FEMPTY", name="Empty Synthetic Faculty"),
    ])
    db_session.commit()
    db_session.add_all([
        Department(id="dept-syn-001", code="DSYN", name="Synthetic Department", faculty_id="fac-syn-001"),
        Department(id="dept-free-002", code="DFREE", name="Unreferenced Department", faculty_id="fac-syn-001"),
        ServiceUnit(id="unit-syn-001", code="USYN", name="Synthetic Unit"),
        ServiceUnit(id="unit-free-002", code="UFREE", name="Unreferenced Unit"),
    ])
    db_session.commit()


def add_responsibility(db_session, **refs):
    db_session.add(ServiceResponsibility(
        id="resp-syn-001",
        user_id="usr-syn-001",
        role_title="Coordinator",
        status=ResponsibilityStatus.INACTIVE,
        **refs,
    ))
    db_session.commit()


def assert_conflict(response, code):
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    return body["error"]["message"]


def test_faculty_with_departments_rejected(client, db_session):
    seed(db_session)
    message = assert_conflict(client.delete("/faculties/fac-syn-001"), "FACULTY_HAS_DEPENDENCIES")
    assert "2 department(s)" in message
    assert db_session.query(Department).filter(Department.faculty_id == "fac-syn-001").count() == 2


def test_faculty_without_dependencies_deleted(client, db_session):
    seed(db_session)
    assert client.delete("/faculties/fac-empty-002").status_code == 200
    assert client.get("/faculties/fac-empty-002").status_code == 404


def test_department_with_affiliations_rejected(client, db_session):
    seed(db_session)
    db_session.add(UserAffiliation(
        id="aff-syn-001", user_id="usr-syn-001", department_id="dept-syn-001", faculty_id="fac-syn-001"
    ))
    db_session.commit()

    assert_conflict(client.delete("/departments/dept-syn-001"), "DEPARTMENT_HAS_DEPENDENCIES")
    assert db_session.query(UserAffiliation).count() == 1


def test_department_with_responsibilities_rejected(client, db_session):
    seed(db_session)
    add_responsibility(db_session, department_id="dept-syn-001")
    message = assert_conflict(client.delete("/departments/dept-syn-001"), "DEPARTMENT_HAS_DEPENDENCIES")
    assert "1 responsibility(ies)" in message


def test_department_without_dependencies_deleted(client, db_session):
    seed(db_session)
    assert client.delete("/departments/dept-free-002").status_code == 200
    assert client.get("/departments/dept-free-002").status_code == 404


def test_service_unit_with_responsibilities_rejected(client, db_session):
    seed(db_session)
    add_responsibility(db_session, service_unit_id="unit-syn-001")
    assert_conflict(client.delete("/service-units/unit-syn-001"), "SERVICE_UNIT_HAS_DEPENDENCIES")
    assert db_session.query(ServiceResponsibility).count() == 1


def test_service_unit_without_dependencies_deleted(client, db_session):
    seed(db_session)
    assert client.delete("/service-units/unit-free-002").status_code == 200
    assert client.get("/service-units/unit-free-002").status_code == 404
