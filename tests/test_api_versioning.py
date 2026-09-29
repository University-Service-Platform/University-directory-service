"""/api/v1 is the documented API; unprefixed paths remain as hidden, deprecated aliases."""
from app.main import app
from app.models.faculty import Faculty
from tests.auth_support import STAFF_TOKEN, bearer


def seed(db_session):
    db_session.add(Faculty(id="fac-syn-001", code="FSYN", name="Synthetic Faculty"))
    db_session.commit()


def test_versioned_route_has_no_deprecation_header(client, db_session):
    seed(db_session)
    response = client.get("/api/v1/faculties/fac-syn-001")
    assert response.status_code == 200
    assert "deprecation" not in response.headers


def test_legacy_alias_still_works_and_is_marked_deprecated(client, db_session):
    seed(db_session)
    response = client.get("/faculties/fac-syn-001")

    assert response.status_code == 200
    assert response.json()["data"]["code"] == "FSYN"
    assert response.headers["deprecation"] == "true"
    assert response.headers["link"] == '</api/v1/faculties/fac-syn-001>; rel="successor-version"'


def test_legacy_validation_alias_still_works(client, db_session):
    seed(db_session)
    response = client.get("/validation/faculties/FSYN")
    assert response.status_code == 200
    assert response.json()["data"]["is_valid"] is True


def test_legacy_alias_enforces_same_auth(anon_client, db_session):
    seed(db_session)
    assert anon_client.get("/faculties").status_code == 401
    response = anon_client.post("/faculties", json={"code": "FX", "name": "Synthetic X"}, headers=bearer(STAFF_TOKEN))
    assert response.status_code == 403


def test_responsibilities_have_no_legacy_alias(client):
    assert client.get("/responsibilities").status_code == 404


def test_health_stays_at_root(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/api/v1/health").status_code == 404


def test_openapi_documents_only_versioned_routes():
    paths = set(app.openapi()["paths"])

    assert "/health" in paths
    assert {
        "/api/v1/faculties",
        "/api/v1/departments",
        "/api/v1/service-units",
        "/api/v1/affiliations",
        "/api/v1/responsibilities",
        "/api/v1/validation/users/{user_id}/affiliation",
        "/api/v1/validation/users/{user_id}/responsibilities",
    } <= paths
    assert not [p for p in paths if p not in ("/health",) and not p.startswith("/api/v1/")]
