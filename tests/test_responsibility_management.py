"""Service responsibility CRUD (synthetic data; Identity Service faked)."""
import pytest

from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_responsibility import ServiceResponsibility
from app.models.service_unit import ServiceUnit
from tests.auth_support import STAFF_TOKEN, bearer


def seed(db_session):
    db_session.add_all([
        Faculty(id="fac-syn-001", code="FSYN", name="Synthetic Faculty"),
        Faculty(id="fac-syn-002", code="FSYN2", name="Other Synthetic Faculty"),
        ServiceUnit(id="unit-syn-001", code="USYN", name="Synthetic Service Unit"),
    ])
    db_session.commit()
    db_session.add(Department(id="dept-syn-001", code="DSYN", name="Synthetic Department", faculty_id="fac-syn-001"))
    db_session.commit()


def payload(**overrides):
    body = {"user_id": "usr-syn-001", "service_unit_id": "unit-syn-001", "role_title": "Unit Coordinator"}
    body.update(overrides)
    return body


def create(client, **overrides):
    return client.post("/api/v1/responsibilities", json=payload(**overrides))


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.json()
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == code


# ----------------------------------------------------------------- create

def test_create_responsibility(client, db_session, identity_client):
    seed(db_session)
    response = create(client, department_id="DSYN", faculty_id="fsyn")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_id"] == "usr-syn-001"
    assert data["service_unit_id"] == "unit-syn-001"
    assert data["service_unit_code"] == "USYN"
    assert data["department_id"] == "dept-syn-001"  # resolved from code
    assert data["faculty_id"] == "fac-syn-001"
    assert data["status"] == "ACTIVE"
    assert identity_client.calls == ["usr-syn-001"]


def test_create_requires_an_organizational_target(client, db_session):
    seed(db_session)
    response = client.post("/api/v1/responsibilities", json={"user_id": "usr-syn-001", "role_title": "Floating"})
    assert_error(response, 422, "VALIDATION_ERROR")


@pytest.mark.parametrize("field,value,code", [
    ("service_unit_id", "unit-missing", "SERVICE_UNIT_NOT_FOUND"),
    ("department_id", "dept-missing", "DEPARTMENT_NOT_FOUND"),
    ("faculty_id", "fac-missing", "FACULTY_NOT_FOUND"),
])
def test_create_rejects_unknown_units(client, db_session, field, value, code):
    seed(db_session)
    assert_error(create(client, **{field: value}), 404, code)


def test_create_rejects_department_outside_faculty(client, db_session):
    seed(db_session)
    response = create(client, department_id="dept-syn-001", faculty_id="fac-syn-002")
    assert_error(response, 400, "INVALID_ORGANIZATIONAL_RELATIONSHIP")


def test_create_rejects_invalid_user_identifier(client, db_session, identity_client):
    seed(db_session)
    assert_error(create(client, user_id="bad user!"), 400, "INVALID_IDENTIFIER_FORMAT")
    assert identity_client.calls == []


def test_create_rejects_unknown_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.missing.add("usr-ghost")
    assert_error(create(client, user_id="usr-ghost"), 404, "USER_NOT_FOUND")
    assert db_session.query(ServiceResponsibility).count() == 0


def test_create_rejects_inactive_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.inactive.add("usr-left")
    assert_error(create(client, user_id="usr-left"), 409, "USER_INACTIVE")


def test_create_fails_closed_when_identity_unavailable(client, db_session, identity_client):
    seed(db_session)
    identity_client.go_down()
    assert_error(create(client), 503, "IDENTITY_SERVICE_UNAVAILABLE")
    assert db_session.query(ServiceResponsibility).count() == 0


def test_duplicate_active_responsibility_rejected(client, db_session):
    seed(db_session)
    assert create(client).status_code == 201
    assert_error(create(client, role_title="Another Title"), 409, "RESPONSIBILITY_ALREADY_EXISTS")


def test_inactive_record_does_not_block_new_active_one(client, db_session):
    seed(db_session)
    assert create(client, status="INACTIVE").status_code == 201
    assert create(client).status_code == 201


def test_same_user_different_unit_allowed(client, db_session):
    seed(db_session)
    assert create(client).status_code == 201
    assert create(client, service_unit_id=None, department_id="dept-syn-001").status_code == 201


# ----------------------------------------------------------------- read

def test_list_and_filter(client, db_session):
    seed(db_session)
    create(client)
    create(client, user_id="usr-syn-002", status="INACTIVE")

    assert len(client.get("/api/v1/responsibilities").json()["data"]) == 2
    active = client.get("/api/v1/responsibilities", params={"status": "ACTIVE"}).json()["data"]
    assert [r["user_id"] for r in active] == ["usr-syn-001"]
    by_user = client.get("/api/v1/responsibilities", params={"user_id": "usr-syn-002"}).json()["data"]
    assert [r["status"] for r in by_user] == ["INACTIVE"]


def test_get_by_id_and_not_found(client, db_session):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    assert client.get(f"/api/v1/responsibilities/{resp_id}").json()["data"]["id"] == resp_id
    assert_error(client.get("/api/v1/responsibilities/resp-missing"), 404, "RESPONSIBILITY_NOT_FOUND")


def test_non_admin_can_read_but_not_write(client, anon_client, db_session):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    headers = bearer(STAFF_TOKEN)

    assert anon_client.get("/api/v1/responsibilities", headers=headers).status_code == 200
    assert anon_client.post("/api/v1/responsibilities", json=payload(user_id="usr-x"), headers=headers).status_code == 403
    assert anon_client.put(f"/api/v1/responsibilities/{resp_id}", json={}, headers=headers).status_code == 403
    assert anon_client.delete(f"/api/v1/responsibilities/{resp_id}", headers=headers).status_code == 403


# ----------------------------------------------------------------- update

def test_update_title_and_scope(client, db_session):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    response = client.put(f"/api/v1/responsibilities/{resp_id}", json={"role_title": "Head of Unit", "department_id": "DSYN"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["role_title"] == "Head of Unit"
    assert data["department_id"] == "dept-syn-001"
    assert data["service_unit_id"] == "unit-syn-001"


def test_deactivate_allowed_for_user_inactive_in_identity(client, db_session, identity_client):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    identity_client.inactive.add("usr-syn-001")
    identity_client.calls.clear()

    response = client.put(f"/api/v1/responsibilities/{resp_id}", json={"status": "INACTIVE"})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "INACTIVE"
    assert identity_client.calls == []


def test_reactivation_rechecks_user_and_duplicates(client, db_session, identity_client):
    seed(db_session)
    old_id = create(client, status="INACTIVE").json()["data"]["id"]
    create(client)  # the active one

    assert_error(client.put(f"/api/v1/responsibilities/{old_id}", json={"status": "ACTIVE"}), 409, "RESPONSIBILITY_ALREADY_EXISTS")

    identity_client.inactive.add("usr-syn-002")
    other_id = create(client, user_id="usr-syn-002", status="INACTIVE").json()["data"]["id"]
    assert_error(client.put(f"/api/v1/responsibilities/{other_id}", json={"status": "ACTIVE"}), 409, "USER_INACTIVE")


def test_update_rejects_unknown_unit(client, db_session):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    assert_error(client.put(f"/api/v1/responsibilities/{resp_id}", json={"service_unit_id": "unit-missing"}), 404, "SERVICE_UNIT_NOT_FOUND")


# ----------------------------------------------------------------- delete

def test_delete_responsibility(client, db_session, identity_client):
    seed(db_session)
    resp_id = create(client).json()["data"]["id"]
    identity_client.inactive.add("usr-syn-001")  # deleting never needs the Identity Service

    assert client.delete(f"/api/v1/responsibilities/{resp_id}").status_code == 200
    assert_error(client.get(f"/api/v1/responsibilities/{resp_id}"), 404, "RESPONSIBILITY_NOT_FOUND")


def test_created_responsibility_passes_existing_validation_endpoint(client, db_session):
    seed(db_session)
    create(client)
    response = client.get("/api/v1/validation/users/usr-syn-001/responsibilities", params={"service_unit_id": "unit-syn-001"})
    assert response.status_code == 200
    assert response.json()["data"]["is_valid"] is True
