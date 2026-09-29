"""Free-text search (?q=) on directory and affiliation lists (synthetic data)."""
import pytest

from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_responsibility import ResponsibilityStatus, ServiceResponsibility
from app.models.service_unit import ServiceUnit
from app.models.user_affiliation import UserAffiliation


def seed(db_session):
    db_session.add_all([
        Faculty(id="fac-syn-001", code="FSYN", name="Faculty of Synthetic Science", description="Synthetic sciences"),
        Faculty(id="fac-syn-002", code="FART", name="Faculty of Synthetic Arts", description="100% synthetic_arts"),
        ServiceUnit(id="unit-syn-001", code="ITHD", name="Synthetic IT Help Desk"),
        ServiceUnit(id="unit-syn-002", code="LIB", name="Synthetic Library", description="Books and study rooms"),
    ])
    db_session.commit()
    db_session.add_all([
        Department(id="dept-syn-001", code="CS", name="Department of Synthetic Computing", faculty_id="fac-syn-001"),
        Department(id="dept-syn-002", code="MATH", name="Department of Synthetic Mathematics", faculty_id="fac-syn-001"),
        Department(id="dept-syn-003", code="MUS", name="Department of Synthetic Music", faculty_id="fac-syn-002"),
    ])
    db_session.commit()
    db_session.add_all([
        UserAffiliation(id="aff-syn-001", user_id="usr-student-001", department_id="dept-syn-001", faculty_id="fac-syn-001"),
        UserAffiliation(id="aff-syn-002", user_id="usr-student-002", department_id="dept-syn-003", faculty_id="fac-syn-002"),
        ServiceResponsibility(id="resp-syn-001", user_id="usr-servicedesk-001", service_unit_id="unit-syn-001",
                              role_title="Service Desk Lead", status=ResponsibilityStatus.ACTIVE),
        ServiceResponsibility(id="resp-syn-002", user_id="usr-staff-002", department_id="dept-syn-002",
                              role_title="Timetable Officer", status=ResponsibilityStatus.ACTIVE),
    ])
    db_session.commit()


def search(client, path, q, **params):
    response = client.get(path, params={"q": q, **params})
    assert response.status_code == 200, response.json()
    return response.json()["data"]


@pytest.mark.parametrize("q,expected", [
    ("fsyn", ["FSYN"]),               # code, case-insensitive
    ("arts", ["FART"]),               # name
    ("sciences", ["FSYN"]),           # description
    ("synthetic", ["FART", "FSYN"]),  # several matches, ordered by code
    ("nothing-matches", []),
])
def test_faculty_search(client, db_session, q, expected):
    seed(db_session)
    assert [f["code"] for f in search(client, "/api/v1/faculties", q)] == expected


def test_search_treats_wildcards_literally(client, db_session):
    seed(db_session)
    assert [f["code"] for f in search(client, "/api/v1/faculties", "100%")] == ["FART"]
    assert [f["code"] for f in search(client, "/api/v1/faculties", "c_arts")] == ["FART"]
    assert [f["code"] for f in search(client, "/api/v1/faculties", "%")] == ["FART"]  # not "match everything"
    assert [f["code"] for f in search(client, "/api/v1/faculties", "_")] == ["FART"]


def test_blank_search_returns_everything(client, db_session):
    seed(db_session)
    assert len(search(client, "/api/v1/faculties", "   ")) == 2


def test_search_too_long_rejected(client, db_session):
    response = client.get("/api/v1/faculties", params={"q": "x" * 101})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_department_search_combines_with_faculty_filter(client, db_session):
    seed(db_session)
    assert [d["code"] for d in search(client, "/api/v1/departments", "synthetic")] == ["CS", "MATH", "MUS"]
    assert [d["code"] for d in search(client, "/api/v1/departments", "synthetic", faculty_id="fac-syn-001")] == ["CS", "MATH"]
    assert [d["code"] for d in search(client, "/api/v1/departments", "math")] == ["MATH"]


def test_service_unit_search(client, db_session):
    seed(db_session)
    assert [u["code"] for u in search(client, "/api/v1/service-units", "help desk")] == ["ITHD"]
    assert [u["code"] for u in search(client, "/api/v1/service-units", "study")] == ["LIB"]


@pytest.mark.parametrize("q,expected", [
    ("student-002", ["aff-syn-002"]),  # user id
    ("music", ["aff-syn-002"]),        # department name
    ("CS", ["aff-syn-001"]),           # department code
    ("synthetic arts", ["aff-syn-002"]),  # faculty name
])
def test_affiliation_search(client, db_session, q, expected):
    seed(db_session)
    assert [a["id"] for a in search(client, "/api/v1/affiliations", q)] == expected


@pytest.mark.parametrize("q,expected", [
    ("desk lead", ["resp-syn-001"]),      # role title
    ("ITHD", ["resp-syn-001"]),           # service unit code
    ("mathematics", ["resp-syn-002"]),    # department name
    ("usr-staff", ["resp-syn-002"]),      # user id
])
def test_responsibility_search(client, db_session, q, expected):
    seed(db_session)
    assert [r["id"] for r in search(client, "/api/v1/responsibilities", q)] == expected


def test_search_is_available_to_any_authenticated_user(anon_client, db_session):
    from tests.auth_support import STAFF_TOKEN, bearer
    seed(db_session)
    response = anon_client.get("/api/v1/departments", params={"q": "cs"}, headers=bearer(STAFF_TOKEN))
    assert response.status_code == 200
    assert anon_client.get("/api/v1/departments", params={"q": "cs"}).status_code == 401
