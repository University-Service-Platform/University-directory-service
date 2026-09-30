import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_code, ensure_identifier, is_valid_code, is_valid_identifier


@pytest.mark.parametrize("value,expected", [
    ("fac-fsc-1a2b3c", True),
    ("AB", True),
    ("a", False),
    ("x" * 51, False),
    ("bad id", False),
    ("bad$id", False),
    ("", False),
    (None, False),
])
def test_identifier_validation(value, expected):
    assert is_valid_identifier(value) is expected


def test_code_validation_limits_length_to_twenty():
    assert is_valid_code("DEPT-CS")
    assert not is_valid_code("X" * 21)


def test_ensure_identifier_raises_project_error():
    with pytest.raises(AppError) as exc_info:
        ensure_identifier("bad id!", "Faculty")
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_IDENTIFIER_FORMAT"
    assert exc_info.value.message == "Faculty identifier 'bad id!' has an invalid format."


def test_ensure_code_uses_display_value_in_message():
    with pytest.raises(AppError) as exc_info:
        ensure_code("BAD CODE", "Faculty", display="bad code")
    assert exc_info.value.message == "Faculty code 'bad code' has an invalid format."


def test_utc_now_is_timezone_aware():
    assert utc_now().tzinfo is not None


def test_request_validation_error_uses_project_format(client):
    response = client.post("/api/v1/faculties", json={"name": "Synthetic Faculty"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed."
    assert any(d["field"] == "body.code" for d in body["error"]["details"])


def test_unknown_route_uses_project_format(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "Not Found"},
    }


def test_sqlite_foreign_keys_enforced(db_session):
    if db_session.bind.dialect.name != "sqlite":
        pytest.skip("PRAGMA foreign_keys only applies to SQLite")
    assert db_session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_postgres_scheme_is_normalised():
    from app.config import load_settings
    settings = load_settings({"DATABASE_URL": "postgres://u:p@db.example.test:5432/directory"})
    assert settings.database_url == "postgresql://u:p@db.example.test:5432/directory"
