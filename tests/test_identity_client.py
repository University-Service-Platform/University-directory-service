"""Identity Service client (Identity API contract v1): every downstream outcome maps to a Directory error. No network."""
import httpx
import pytest

from app.core.errors import AppError
from app.integrations.identity_client import IdentityClient

BASE_URL = "http://identity.test"
LEAKY_TEXT = "Traceback (internal): db-host-7 connection refused at identity/core.py:42"


def make_client(handler, base_url=BASE_URL, authorization=None):
    return IdentityClient(base_url, connect_timeout=1, read_timeout=1, authorization=authorization,
                          transport=httpx.MockTransport(handler))


def user_payload(**overrides):
    data = {
        "user_id": "usr-syn-001",
        "university_id": "SYN0001",
        "name": "Synthetic User",
        "email": "synthetic.user@example.test",
        "account_type": "STAFF",
        "status": "ACTIVE",
        "is_valid": True,
        "roles": ["STAFF", "admin"],
        "is_authorized": True,
        "required_role_checked": None,
    }
    data.update(overrides)
    return {"success": True, "data": data}


def expect_error(client, status_code, code, user_id="usr-syn-001"):
    with pytest.raises(AppError) as exc_info:
        client.get_active_user(user_id)
    error = exc_info.value
    assert error.status_code == status_code
    assert error.code == code
    assert LEAKY_TEXT not in error.message
    return error


def test_active_user_returned_with_normalised_roles():
    seen = {}

    def handler(request):
        seen["url"] = request.url
        return httpx.Response(200, json=user_payload())

    user = make_client(handler).get_active_user("usr-syn-001")

    assert user.user_id == "usr-syn-001"
    assert user.status == "ACTIVE"
    assert user.roles == ("STAFF", "ADMIN")
    assert seen["url"].path == "/api/v1/validation/users/usr-syn-001"
    # require_active is never sent, so a 403 ACCOUNT_INACTIVE can only concern the caller
    assert "require_active" not in seen["url"].params


def test_user_id_is_url_encoded():
    seen = {}

    def handler(request):
        seen["raw_path"] = request.url.raw_path
        return httpx.Response(200, json=user_payload())

    make_client(handler).get_active_user("a/b")
    assert seen["raw_path"].startswith(b"/api/v1/validation/users/a%2Fb")


def test_profile_fields_are_not_exposed():
    user = make_client(lambda r: httpx.Response(200, json=user_payload())).get_active_user("usr-syn-001")
    assert not hasattr(user, "email")
    assert not hasattr(user, "name")


def test_timeout_maps_to_503():
    def handler(request):
        raise httpx.ReadTimeout(LEAKY_TEXT, request=request)

    expect_error(make_client(handler), 503, "IDENTITY_SERVICE_UNAVAILABLE")


def test_connection_error_maps_to_503():
    def handler(request):
        raise httpx.ConnectError(LEAKY_TEXT, request=request)

    expect_error(make_client(handler), 503, "IDENTITY_SERVICE_UNAVAILABLE")


def test_missing_base_url_maps_to_503():
    client = make_client(lambda r: httpx.Response(200, json=user_payload()), base_url=None)
    expect_error(client, 503, "IDENTITY_SERVICE_UNAVAILABLE")


def test_not_found_maps_to_user_not_found():
    body = {"success": False, "error": {"code": "USER_NOT_FOUND", "message": LEAKY_TEXT}}
    error = expect_error(make_client(lambda r: httpx.Response(404, json=body)), 404, "USER_NOT_FOUND")
    assert error.message == "User 'usr-syn-001' was not found in the Identity Service."


def test_caller_account_inactive_maps_to_forbidden():
    body = {"success": False, "error": {"code": "ACCOUNT_INACTIVE", "message": LEAKY_TEXT}}
    expect_error(make_client(lambda r: httpx.Response(403, json=body)), 403, "FORBIDDEN")


def test_caller_token_rejected_maps_to_unauthorized():
    body = {"success": False, "error": {"code": "INVALID_TOKEN", "message": LEAKY_TEXT}}
    error = expect_error(make_client(lambda r: httpx.Response(401, json=body)), 401, "UNAUTHORIZED")
    assert error.headers == {"WWW-Authenticate": "Bearer"}


def test_other_forbidden_maps_to_502():
    body = {"success": False, "error": {"code": "FORBIDDEN", "message": LEAKY_TEXT}}
    expect_error(make_client(lambda r: httpx.Response(403, json=body)), 502, "IDENTITY_SERVICE_ERROR")


@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_server_errors_map_to_502(status_code):
    client = make_client(lambda r: httpx.Response(status_code, text=LEAKY_TEXT))
    expect_error(client, 502, "IDENTITY_SERVICE_ERROR")


def test_malformed_json_maps_to_bad_response():
    client = make_client(lambda r: httpx.Response(200, text="<html>" + LEAKY_TEXT))
    expect_error(client, 502, "IDENTITY_SERVICE_BAD_RESPONSE")


@pytest.mark.parametrize("payload", [
    {"success": True},
    {"success": True, "data": "nope"},
    ["not", "an", "object"],
    user_payload(roles="ADMIN"),
    user_payload(is_valid="yes"),
    user_payload(is_authorized="no"),
    {"success": True, "data": {"user_id": "usr-syn-001"}},
])
def test_unexpected_shape_maps_to_bad_response(payload):
    client = make_client(lambda r: httpx.Response(200, json=payload))
    expect_error(client, 502, "IDENTITY_SERVICE_BAD_RESPONSE")


def test_inactive_target_user_maps_to_user_inactive():
    payload = user_payload(status="INACTIVE", is_valid=False)
    expect_error(make_client(lambda r: httpx.Response(200, json=payload)), 409, "USER_INACTIVE")


def test_lookup_user_reports_inactive_without_raising():
    payload = user_payload(status="INACTIVE", is_valid=False)
    user = make_client(lambda r: httpx.Response(200, json=payload)).lookup_user("usr-syn-001")
    assert user.is_active is False
    assert user.status == "INACTIVE"


def test_caller_authorization_is_forwarded():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=user_payload())

    make_client(handler, authorization="Bearer synthetic.test.token").get_active_user("usr-syn-001")
    assert seen["auth"] == "Bearer synthetic.test.token"


def test_with_authorization_returns_configured_copy():
    client = make_client(lambda r: httpx.Response(200, json=user_payload()))
    copy = client.with_authorization("Bearer x")
    assert copy.authorization == "Bearer x"
    assert client.authorization is None


def test_university_id_resolves_to_canonical_user_id():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return httpx.Response(200, json=user_payload(user_id="usr-student-001", university_id="STU001"))

    user = make_client(handler).get_active_user("STU001")
    assert seen["path"] == "/api/v1/validation/users/STU001"
    assert user.user_id == "usr-student-001"


def test_required_role_is_sent_and_result_reported():
    seen = {}

    def handler(request):
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=user_payload(is_authorized=False, required_role_checked="ADMIN"))

    user = make_client(handler).lookup_user("usr-syn-001", required_role="ADMIN")
    assert seen["params"] == {"required_role": "ADMIN"}
    assert user.is_authorized is False


def test_non_boolean_is_authorized_is_bad_response():
    client = make_client(lambda r: httpx.Response(200, json=user_payload(is_authorized="no")))
    expect_error(client, 502, "IDENTITY_SERVICE_BAD_RESPONSE")
