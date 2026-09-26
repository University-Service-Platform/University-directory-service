"""GET /validation/users/{user_id}/affiliation (synthetic data)."""
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user_affiliation import UserAffiliation

URL = "/validation/users/{}/affiliation"


def seed(db_session):
    db_session.add_all([
        Faculty(id="fac-syn-001", code="FSYN", name="Synthetic Faculty"),
        Faculty(id="fac-syn-002", code="FSYN2", name="Other Synthetic Faculty"),
    ])
    db_session.commit()
    db_session.add_all([
        Department(id="dept-syn-001", code="DSYN", name="Synthetic Department", faculty_id="fac-syn-001"),
        Department(id="dept-syn-002", code="DSYN2", name="Second Synthetic Department", faculty_id="fac-syn-001"),
        Department(id="dept-syn-003", code="DSYN3", name="Other Faculty Department", faculty_id="fac-syn-002"),
    ])
    db_session.commit()
    db_session.add_all([
        UserAffiliation(id="aff-syn-001", user_id="usr-syn-001", department_id="dept-syn-001", faculty_id="fac-syn-001"),
        UserAffiliation(id="aff-syn-002", user_id="usr-syn-001", department_id="dept-syn-002", faculty_id="fac-syn-001"),
    ])
    db_session.commit()


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == code


def test_valid_affiliation_by_department(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"department_id": "dept-syn-001"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_id"] == "usr-syn-001"
    assert data["is_valid"] is True
    assert data["affiliations"] == [{
        "affiliation_id": "aff-syn-001",
        "department": {"id": "dept-syn-001", "code": "DSYN", "name": "Synthetic Department"},
        "faculty": {"id": "fac-syn-001", "code": "FSYN", "name": "Synthetic Faculty"},
    }]


def test_valid_affiliation_by_codes(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"department_id": "dsyn2", "faculty_id": "FSYN"})
    assert response.status_code == 200
    assert [a["affiliation_id"] for a in response.json()["data"]["affiliations"]] == ["aff-syn-002"]


def test_faculty_filter_returns_all_matches(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"faculty_id": "fac-syn-001"})
    assert len(response.json()["data"]["affiliations"]) == 2


def test_no_filters_returns_all_user_affiliations(client, db_session):
    seed(db_session)
    assert len(client.get(URL.format("usr-syn-001")).json()["data"]["affiliations"]) == 2


def test_no_match_returns_affiliation_not_found(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"department_id": "dept-syn-003"})
    assert_error(response, 404, "AFFILIATION_NOT_FOUND")


def test_unknown_user_returns_affiliation_not_found(client, db_session):
    seed(db_session)
    assert_error(client.get(URL.format("usr-nobody")), 404, "AFFILIATION_NOT_FOUND")


def test_unknown_department_returns_department_not_found(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"department_id": "dept-missing"})
    assert_error(response, 404, "DEPARTMENT_NOT_FOUND")


def test_department_outside_faculty_rejected(client, db_session):
    seed(db_session)
    response = client.get(URL.format("usr-syn-001"), params={"department_id": "dept-syn-001", "faculty_id": "fac-syn-002"})
    assert_error(response, 400, "INVALID_ORGANIZATIONAL_RELATIONSHIP")


def test_invalid_user_identifier_rejected(client, db_session):
    seed(db_session)
    assert_error(client.get(URL.format("bad$user")), 400, "INVALID_IDENTIFIER_FORMAT")


def test_does_not_call_identity_service(client, db_session, identity_client):
    seed(db_session)
    client.get(URL.format("usr-syn-001"))
    assert identity_client.calls == []


def test_requires_token(anon_client, db_session):
    seed(db_session)
    assert anon_client.get(URL.format("usr-syn-001")).status_code == 401
