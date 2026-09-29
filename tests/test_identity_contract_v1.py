"""Behaviour required by the Identity Service API contract v1 (synthetic data; Identity faked)."""
from app.auth import get_token_verifier
from app.auth.principal import Principal
from app.main import app
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_responsibility import ServiceResponsibility
from app.models.service_unit import ServiceUnit
from app.models.user_affiliation import UserAffiliation
from tests.auth_support import bearer, make_rs256_token

FACULTY = {"code": "FSYN", "name": "Synthetic Faculty"}


def seed(db_session):
    db_session.add_all([
        Faculty(id="fac-syn-001", code="FSYN0", name="Synthetic Faculty Zero"),
        ServiceUnit(id="unit-syn-001", code="USYN", name="Synthetic Unit"),
    ])
    db_session.commit()
    db_session.add(Department(id="dept-syn-001", code="DSYN", name="Synthetic Department", faculty_id="fac-syn-001"))
    db_session.commit()


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.json()
    assert response.json()["error"]["code"] == code


# ------------------------------------------------ token roles are a snapshot: confirm live before writes

def test_admin_write_confirms_role_live(client, identity_client):
    assert client.post("/api/v1/faculties", json=FACULTY).status_code == 201
    assert identity_client.role_checks == [("usr-admin-001", "ADMIN")]


def test_admin_role_revoked_after_login_is_forbidden(client, identity_client):
    identity_client.roles["usr-admin-001"] = ("STAFF",)  # token still says ADMIN
    response = client.post("/api/v1/faculties", json=FACULTY)
    assert_error(response, 403, "FORBIDDEN")
    assert response.json()["error"]["message"] == "This operation requires one of the roles: ADMIN."


def test_admin_deactivated_after_login_is_forbidden(client, identity_client):
    identity_client.inactive.add("usr-admin-001")
    response = client.post("/api/v1/faculties", json=FACULTY)
    assert_error(response, 403, "FORBIDDEN")
    assert response.json()["error"]["message"] == "Your account is not active."


def test_admin_deleted_after_login_is_unauthorized(client, identity_client):
    identity_client.missing.add("usr-admin-001")
    assert_error(client.post("/api/v1/faculties", json=FACULTY), 401, "UNAUTHORIZED")


def test_write_fails_closed_when_identity_unavailable(client, identity_client):
    identity_client.go_down()
    assert_error(client.post("/api/v1/faculties", json=FACULTY), 503, "IDENTITY_SERVICE_UNAVAILABLE")


def test_reads_need_no_identity_call_in_jwks_mode(client, identity_client):
    assert client.get("/api/v1/faculties").status_code == 200
    assert client.get("/api/v1/validation/faculties/fac-x-1").status_code == 404
    assert identity_client.role_checks == [] and identity_client.calls == [] and identity_client.lookups == []


def test_roles_verified_live_skip_second_check(anon_client, identity_client):
    """identity-hs256 already reads roles live, so require_roles must not call again."""
    class LiveVerifier:
        def verify(self, token):
            return Principal.build("usr-admin-001", ["ADMIN"], roles_verified_live=True)

    app.dependency_overrides[get_token_verifier] = lambda: LiveVerifier()
    response = anon_client.post("/api/v1/faculties", json=FACULTY, headers=bearer("opaque"))
    assert response.status_code == 201
    assert identity_client.role_checks == []


def test_non_admin_token_rejected_without_identity_call(anon_client, identity_client):
    token = make_rs256_token("usr-staff-009", ["STAFF"])
    assert_error(anon_client.post("/api/v1/faculties", json=FACULTY, headers=bearer(token)), 403, "FORBIDDEN")
    assert identity_client.role_checks == []


# ------------------------------------------------ users are referenced by their canonical id (JWT `sub`)

def test_affiliation_stores_canonical_user_id(client, db_session, identity_client):
    seed(db_session)
    identity_client.aliases["STU001"] = "usr-student-001"

    response = client.post("/api/v1/affiliations", json={"user_id": "STU001", "department_id": "DSYN"})

    assert response.status_code == 201
    assert response.json()["data"]["user_id"] == "usr-student-001"
    assert db_session.query(UserAffiliation).one().user_id == "usr-student-001"
    # a second request by university id is recognised as the same user
    dup = client.post("/api/v1/affiliations", json={"user_id": "STU001", "department_id": "DSYN"})
    assert_error(dup, 409, "AFFILIATION_ALREADY_EXISTS")


def test_responsibility_stores_canonical_user_id(client, db_session, identity_client):
    seed(db_session)
    identity_client.aliases["SDO001"] = "usr-servicedesk-001"
    body = {"user_id": "SDO001", "service_unit_id": "USYN", "role_title": "Service Desk Lead"}

    response = client.post("/api/v1/responsibilities", json=body)

    assert response.status_code == 201
    assert response.json()["data"]["user_id"] == "usr-servicedesk-001"
    assert_error(client.post("/api/v1/responsibilities", json=body), 409, "RESPONSIBILITY_ALREADY_EXISTS")


def test_inactive_responsibility_still_requires_existing_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.missing.add("usr-ghost")
    body = {"user_id": "usr-ghost", "service_unit_id": "USYN", "role_title": "Historic", "status": "INACTIVE"}
    assert_error(client.post("/api/v1/responsibilities", json=body), 404, "USER_NOT_FOUND")
    assert db_session.query(ServiceResponsibility).count() == 0


def test_inactive_responsibility_allowed_for_inactive_user(client, db_session, identity_client):
    seed(db_session)
    identity_client.inactive.add("usr-left")
    body = {"user_id": "usr-left", "service_unit_id": "USYN", "role_title": "Former Lead", "status": "INACTIVE"}
    response = client.post("/api/v1/responsibilities", json=body)
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "INACTIVE"
