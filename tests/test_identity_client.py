"""Identity Service client: every downstream outcome maps to a Directory error. No network."""
import httpx
import pytest

from app.core.errors import AppError
from app.integrations.identity_client import IdentityClient

BASE_URL = "http://identity.test"
LEAKY_TEXT = "Traceback (internal): db-host-7 connection refused at identity/core.py:42"


def make_client(handler, base_url=BASE_URL):
    return IdentityClient(base_url, connect_timeout=1, read_timeout=1, transport=httpx.MockTransport(handler))


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
    assert seen["url"].path == "/validation/users/usr-syn-001"
    assert seen["url"].params["require_active"] == "true"


def test_user_id_is_url_encoded():
    seen = {}

    def handler(request):
        seen["raw_path"] = request.url.raw_path
        return httpx.Response(200, json=user_payload())

    make_client(handler).get_active_user("a/b")
    assert seen["raw_path"].startswith(b"/validation/users/a%2Fb")


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


def test_account_inactive_maps_to_user_inactive():
    body = {"success": False, "error": {"code": "ACCOUNT_INACTIVE", "message": LEAKY_TEXT}}
    expect_error(make_client(lambda r: httpx.Response(403, json=body)), 409, "USER_INACTIVE")


def test_inactive_flag_in_success_body_maps_to_user_inactive():
    payload = user_payload(status="INACTIVE", is_valid=False)
    expect_error(make_client(lambda r: httpx.Response(200, json=payload)), 409, "USER_INACTIVE")


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
    {"success": True, "data": {"user_id": "usr-syn-001"}},
])
def test_unexpected_shape_maps_to_bad_response(payload):
    client = make_client(lambda r: httpx.Response(200, json=payload))
    expect_error(client, 502, "IDENTITY_SERVICE_BAD_RESPONSE")
