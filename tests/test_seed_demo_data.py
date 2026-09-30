"""The demo seed script loads its synthetic data through the real API and is idempotent."""
import pytest

from scripts import seed_demo_data as seed_script

# Canonical Identity user ids for the Identity Service's synthetic demo users.
DEMO_USERS = {
    "STF001": "usr-staff-001",
    "STU001": "usr-student-001",
    "STU003": "usr-student-003",
    "ACD001": "usr-academic-001",
    "ADS001": "usr-adminstaff-001",
    "SDO001": "usr-servicedesk-001",
    "TEC001": "usr-technician-001",
    "RMG001": "usr-resourcemgr-001",
    "EVO001": "usr-organizer-001",
}


@pytest.fixture
def demo_identity(identity_client):
    identity_client.aliases.update(DEMO_USERS)
    return identity_client


def run_seed(client):
    return seed_script.seed(client, headers={}, log=lambda line: None)


def test_seed_creates_all_demo_records(client, db_session, demo_identity):
    counts = run_seed(client)

    expected = (len(seed_script.FACULTIES) + len(seed_script.DEPARTMENTS) + len(seed_script.SERVICE_UNITS)
                + len(seed_script.AFFILIATIONS) + len(seed_script.RESPONSIBILITIES))
    assert counts == {"created": expected, "skipped": 0}
    assert len(client.get("/api/v1/faculties").json()["data"]) == len(seed_script.FACULTIES)
    assert len(client.get("/api/v1/service-units").json()["data"]) == len(seed_script.SERVICE_UNITS)


def test_seed_is_idempotent(client, db_session, demo_identity):
    first = run_seed(client)
    second = run_seed(client)
    assert second == {"created": 0, "skipped": first["created"]}


def test_seeded_data_supports_the_team_workflows(client, db_session, demo_identity):
    run_seed(client)

    # users are stored by canonical Identity id, not university id
    student = client.get("/api/v1/validation/users/usr-student-001/affiliation", params={"department_id": "CS"})
    assert student.status_code == 200
    assert student.json()["data"]["affiliations"][0]["faculty"]["code"] == "FSC"
    second_student = client.get("/api/v1/validation/users/usr-student-003/affiliation",
                                params={"department_id": "SE"})
    assert second_student.status_code == 200
    assert second_student.json()["data"]["affiliations"][0]["faculty"]["code"] == "FCT"

    desk = client.get("/api/v1/responsibilities", params={"q": "ITHD", "status": "ACTIVE"}).json()["data"]
    assert {r["user_id"] for r in desk} == {"usr-servicedesk-001", "usr-technician-001"}

    cs = client.get("/api/v1/validation/departments/CS").json()["data"]
    manager = client.get("/api/v1/validation/users/usr-resourcemgr-001/responsibilities",
                         params={"department_id": cs["department_id"]})
    assert manager.status_code == 200


def test_seed_reports_unexpected_errors(client, db_session, demo_identity):
    demo_identity.missing.add("STU001")
    with pytest.raises(seed_script.SeedError, match="USER_NOT_FOUND"):
        run_seed(client)
