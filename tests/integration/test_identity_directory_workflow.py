"""Cross-service integration test: Identity Service <-> Directory Service (real services over HTTP).

Skipped unless both services are running and these environment variables are set:

    IT_DIRECTORY_BASE_URL   e.g. http://localhost:8002
    IT_IDENTITY_BASE_URL    e.g. http://localhost:8001
    IT_ADMIN_USERNAME / IT_ADMIN_PASSWORD      synthetic ADMIN account (e.g. ADM001)
    IT_STAFF_USERNAME / IT_STAFF_PASSWORD      synthetic non-admin account (e.g. STF001)
    IT_STUDENT_USERNAME                        synthetic student university id (e.g. STU001)
    IT_RESPONSIBLE_USERNAME                    synthetic staff university id (e.g. SDO001)
    IT_INACTIVE_USERNAME (optional)            synthetic inactive account (e.g. STU002)

The Identity Service must have DIRECTORY_SERVICE_BASE_URL pointing at the Directory Service for
the eligibility steps. Run with:  pytest -m integration tests/integration -v

Workflow covered (the platform's "authenticated service access" and key business rule):
  1. Admin logs in at Identity and gets an RS256 token.
  2. Directory accepts that token (JWKS) and confirms ADMIN live with Identity on each write.
  3. Admin creates a faculty, department and service unit in Directory.
  4. Admin affiliates a student by university id; Directory verifies the user with Identity and
     stores the canonical Identity user id.
  5. Admin assigns a service responsibility to a staff member.
  6. Identity's eligibility endpoint calls Directory back (forwarding the token) and reports the
     student affiliated / the staff member responsible.
  7. A non-admin token is refused for writes; an inactive account cannot be affiliated.
All data is synthetic, uniquely suffixed per run and deleted at the end.
"""
import os
import uuid

import httpx
import pytest

REQUIRED = ["IT_DIRECTORY_BASE_URL", "IT_IDENTITY_BASE_URL", "IT_ADMIN_USERNAME", "IT_ADMIN_PASSWORD",
            "IT_STAFF_USERNAME", "IT_STAFF_PASSWORD", "IT_STUDENT_USERNAME", "IT_RESPONSIBLE_USERNAME"]
MISSING = [name for name in REQUIRED if not os.environ.get(name)]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(bool(MISSING), reason=f"integration environment not configured: {', '.join(MISSING)}"),
]


def env(name):
    return os.environ[name]


@pytest.fixture(scope="module")
def identity():
    with httpx.Client(base_url=os.environ.get("IT_IDENTITY_BASE_URL", ""), timeout=15) as client:
        yield client


@pytest.fixture(scope="module")
def directory():
    with httpx.Client(base_url=os.environ.get("IT_DIRECTORY_BASE_URL", ""), timeout=15) as client:
        yield client


def login(identity, username, password):
    response = identity.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data


def canonical_id(identity, headers, university_id):
    response = identity.get(f"/api/v1/validation/users/{university_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]["user_id"]


def test_identity_and_directory_workflow(identity, directory):
    admin, admin_data = login(identity, env("IT_ADMIN_USERNAME"), env("IT_ADMIN_PASSWORD"))
    staff, _ = login(identity, env("IT_STAFF_USERNAME"), env("IT_STAFF_PASSWORD"))
    assert "ADMIN" in admin_data["roles"]

    suffix = uuid.uuid4().hex[:5].upper()
    created = []  # (path, id) for cleanup, newest first
    try:
        # --- 2/3. Directory accepts Identity tokens; admin creates organisational units
        faculty = directory.post("/api/v1/faculties", headers=admin,
                                 json={"code": f"ITF{suffix}", "name": f"Integration Synthetic Faculty {suffix}"})
        assert faculty.status_code == 201, faculty.text
        faculty = faculty.json()["data"]
        created.insert(0, ("/api/v1/faculties", faculty["id"]))

        department = directory.post("/api/v1/departments", headers=admin, json={
            "code": f"ITD{suffix}", "name": f"Integration Synthetic Department {suffix}", "faculty_id": faculty["code"]})
        assert department.status_code == 201, department.text
        department = department.json()["data"]
        created.insert(0, ("/api/v1/departments", department["id"]))

        unit = directory.post("/api/v1/service-units", headers=admin,
                              json={"code": f"ITU{suffix}", "name": f"Integration Synthetic Unit {suffix}"})
        assert unit.status_code == 201, unit.text
        unit = unit.json()["data"]
        created.insert(0, ("/api/v1/service-units", unit["id"]))

        # --- 7a. non-admin cannot write, but can read
        refused = directory.post("/api/v1/faculties", headers=staff, json={"code": f"ITX{suffix}", "name": "Refused"})
        assert refused.status_code == 403 and refused.json()["error"]["code"] == "FORBIDDEN"
        assert directory.get("/api/v1/faculties", headers=staff, params={"q": suffix}).status_code == 200

        # --- 4. affiliation by university id is verified with Identity and stored canonically
        student_id = canonical_id(identity, admin, env("IT_STUDENT_USERNAME"))
        affiliation = directory.post("/api/v1/affiliations", headers=admin, json={
            "user_id": env("IT_STUDENT_USERNAME"), "department_id": department["id"]})
        assert affiliation.status_code == 201, affiliation.text
        affiliation = affiliation.json()["data"]
        created.insert(0, ("/api/v1/affiliations", affiliation["id"]))
        assert affiliation["user_id"] == student_id

        # --- 5. responsibility for a staff member
        responsible_id = canonical_id(identity, admin, env("IT_RESPONSIBLE_USERNAME"))
        responsibility = directory.post("/api/v1/responsibilities", headers=admin, json={
            "user_id": env("IT_RESPONSIBLE_USERNAME"), "service_unit_id": unit["id"],
            "role_title": "Integration Synthetic Lead"})
        assert responsibility.status_code == 201, responsibility.text
        responsibility = responsibility.json()["data"]
        created.insert(0, ("/api/v1/responsibilities", responsibility["id"]))
        assert responsibility["user_id"] == responsible_id

        # Directory validation APIs (what Groups 6-8 call)
        valid = directory.get(f"/api/v1/validation/users/{student_id}/affiliation", headers=staff,
                              params={"department_id": department["id"]})
        assert valid.status_code == 200 and valid.json()["data"]["is_valid"] is True

        # --- 6. Identity eligibility calls Directory back with the forwarded token
        eligible = identity.get(f"/api/v1/validation/users/{student_id}/eligibility", headers=staff, params={
            "relationship": "AFFILIATION", "department_id": department["id"]})
        assert eligible.status_code == 200, eligible.text
        assert eligible.json()["data"]["eligible"] is True, eligible.json()

        responsible = identity.get(f"/api/v1/validation/users/{responsible_id}/eligibility", headers=staff, params={
            "relationship": "RESPONSIBILITY", "service_unit_id": unit["id"]})
        assert responsible.status_code == 200, responsible.text
        assert responsible.json()["data"]["eligible"] is True, responsible.json()

        not_responsible = identity.get(f"/api/v1/validation/users/{student_id}/eligibility", headers=staff, params={
            "relationship": "RESPONSIBILITY", "service_unit_id": unit["id"]})
        assert not_responsible.status_code == 200, not_responsible.text
        assert not_responsible.json()["data"]["eligible"] is False

        # --- 7b. an inactive account cannot be affiliated
        inactive = os.environ.get("IT_INACTIVE_USERNAME")
        if inactive:
            rejected = directory.post("/api/v1/affiliations", headers=admin, json={
                "user_id": inactive, "department_id": department["id"]})
            assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "USER_INACTIVE", rejected.text

        # delete protection while dependents exist
        blocked = directory.delete(f"/api/v1/departments/{department['id']}", headers=admin)
        assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "DEPARTMENT_HAS_DEPENDENCIES"
    finally:
        for path, entity_id in created:
            directory.delete(f"{path}/{entity_id}", headers=admin)

    for path, entity_id in created:
        assert directory.get(f"{path}/{entity_id}", headers=admin).status_code == 404
