"""Affiliation writes verify the user through the Identity Service (faked; no network)."""
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user_affiliation import UserAffiliation


def seed(db_session):
    # Synthetic test data.
    db_session.add(Faculty(id="fac-syn-001", code="FSYN", name="Synthetic Faculty"))
    db_session.commit()
    db_session.add_all([
        Department(id="dept-syn-001", code="DSYN", name="Synthetic Department", faculty_id="fac-syn-001"),
        Department(id="dept-syn-002", code="DSYN2", name="Second Synthetic Department", faculty_id="fac-syn-001"),
    ])
    db_session.commit()


def create(client, user_id="usr-syn-001", department_id="dept-syn-001"):
    return client.post("/api/v1/affiliations", json={"user_id": user_id, "department_id": department_id})


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code


def test_create_checks_identity_service(client, db_session, identity_client):
    seed(db_session)
    assert create(client).status_code == 201
    assert identity_client.calls == ["usr-syn-001"]


def test_create_rejects_unknown_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.missing.add("usr-ghost")
    assert_error(create(client, "usr-ghost"), 404, "USER_NOT_FOUND")
    assert db_session.query(UserAffiliation).count() == 0


def test_create_rejects_inactive_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.inactive.add("usr-left")
    assert_error(create(client, "usr-left"), 409, "USER_INACTIVE")
    assert db_session.query(UserAffiliation).count() == 0


def test_create_fails_closed_when_identity_unavailable(client, db_session, identity_client):
    seed(db_session)
    identity_client.go_down()
    assert_error(create(client), 503, "IDENTITY_SERVICE_UNAVAILABLE")
    assert db_session.query(UserAffiliation).count() == 0


def test_invalid_user_id_rejected_before_calling_identity(client, db_session, identity_client):
    seed(db_session)
    assert_error(create(client, "bad user!"), 400, "INVALID_IDENTIFIER_FORMAT")
    assert identity_client.calls == []


def test_update_rechecks_user(client, db_session, identity_client):
    seed(db_session)
    aff_id = create(client).json()["data"]["id"]

    identity_client.inactive.add("usr-syn-001")
    response = client.put(f"/api/v1/affiliations/{aff_id}", json={"department_id": "dept-syn-002"})

    assert_error(response, 409, "USER_INACTIVE")
    assert db_session.get(UserAffiliation, aff_id).department_id == "dept-syn-001"


def test_update_succeeds_for_active_user(client, db_session, identity_client):
    seed(db_session)
    aff_id = create(client).json()["data"]["id"]
    response = client.put(f"/api/v1/affiliations/{aff_id}", json={"department_id": "dept-syn-002"})
    assert response.status_code == 200
    assert identity_client.calls == ["usr-syn-001", "usr-syn-001"]


def test_reads_do_not_call_identity(client, db_session, identity_client):
    seed(db_session)
    aff_id = create(client).json()["data"]["id"]
    identity_client.calls.clear()
    assert client.get(f"/api/v1/affiliations/{aff_id}").status_code == 200
    assert client.get("/api/v1/affiliations").status_code == 200
    assert identity_client.calls == []
