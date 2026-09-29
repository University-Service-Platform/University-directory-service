"""Authentication and authorization. Tokens are signed with locally generated keys; no network."""
import time

import jwt
import pytest

from app.auth.dependencies import build_token_verifier
from app.auth.verifiers import (
    IdentityHs256TokenVerifier,
    InvalidTokenError,
    JwksKeyStore,
    JwksTokenVerifier,
)
from app.config import load_settings
from app.core.errors import AppError
from app.integrations.identity_client import IdentityUser
from tests.auth_support import (
    OTHER_KEY,
    STAFF_TOKEN,
    TEST_AUDIENCE,
    TEST_ISSUER,
    bearer,
    jwks_document,
    make_rs256_token,
    make_test_verifier,
    public_jwk,
)

FACULTY_PAYLOAD = {"code": "FSYN", "name": "Synthetic Faculty"}


def assert_unauthorized(response):
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# API behaviour (applies to every verifier: both feed the same Principal)
# ---------------------------------------------------------------------------

def test_missing_token_rejected_on_management_endpoint(anon_client):
    assert_unauthorized(anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD))


def test_missing_token_rejected_on_read_endpoint(anon_client):
    assert_unauthorized(anon_client.get("/api/v1/faculties"))


def test_missing_token_rejected_on_validation_endpoint(anon_client):
    assert_unauthorized(anon_client.get("/api/v1/validation/faculties/fac-x-1"))


def test_malformed_token_rejected(anon_client):
    assert_unauthorized(anon_client.get("/api/v1/faculties", headers=bearer("not-a-jwt")))


def test_bad_signature_rejected(anon_client):
    token = make_rs256_token(key=OTHER_KEY)
    assert_unauthorized(anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(token)))


def test_expired_token_rejected(anon_client):
    token = make_rs256_token(expires_in=-60)
    response = anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(token))
    assert_unauthorized(response)
    assert response.json()["error"]["message"] == "Authentication token has expired."


def test_wrong_issuer_rejected(anon_client):
    token = make_rs256_token(issuer="someone-else")
    assert_unauthorized(anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(token)))


def test_wrong_audience_rejected(anon_client):
    token = make_rs256_token(audience="another-service")
    assert_unauthorized(anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(token)))


def test_non_admin_forbidden_on_management_endpoint(anon_client):
    response = anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(STAFF_TOKEN))
    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "FORBIDDEN",
        "message": "This operation requires one of the roles: ADMIN.",
    }


@pytest.mark.parametrize("method,path", [
    ("put", "/api/v1/faculties/fac-x-1"),
    ("delete", "/api/v1/faculties/fac-x-1"),
    ("patch", "/api/v1/departments/dept-x-1"),
    ("delete", "/api/v1/service-units/unit-x-1"),
    ("post", "/api/v1/affiliations"),
])
def test_non_admin_forbidden_on_every_write(anon_client, method, path):
    response = getattr(anon_client, method)(path, headers=bearer(STAFF_TOKEN), **({"json": {}} if method != "delete" else {}))
    assert response.status_code == 403


def test_non_admin_can_read(anon_client):
    response = anon_client.get("/api/v1/faculties", headers=bearer(STAFF_TOKEN))
    assert response.status_code == 200


def test_admin_allowed(anon_client):
    token = make_rs256_token(roles=["admin"])  # role matching is case-insensitive
    response = anon_client.post("/api/v1/faculties", json=FACULTY_PAYLOAD, headers=bearer(token))
    assert response.status_code == 201


def test_health_is_public(anon_client):
    assert anon_client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# JWKS verifier (target contract)
# ---------------------------------------------------------------------------

def test_jwks_verifier_builds_principal():
    principal = make_test_verifier().verify(make_rs256_token("usr-1", ["ADMIN", "staff"]))
    assert principal.user_id == "usr-1"
    assert principal.roles == frozenset({"ADMIN", "STAFF"})


def test_jwks_verifier_missing_roles_claim_means_no_roles():
    principal = make_test_verifier().verify(make_rs256_token(roles=None))
    assert principal.roles == frozenset()


@pytest.mark.parametrize("token_kwargs", [
    {"drop": ["exp"]},
    {"drop": ["sub"]},
    {"drop": ["iss"]},
    {"drop": ["aud"]},
    {"extra": {"roles": "ADMIN"}},
    {"kid": "unknown-kid"},
])
def test_jwks_verifier_rejects_incomplete_tokens(token_kwargs):
    with pytest.raises(InvalidTokenError):
        make_test_verifier().verify(make_rs256_token(**token_kwargs))


def test_jwks_verifier_rejects_hs256_and_none_algorithms():
    now = int(time.time())
    claims = {"sub": "usr-1", "iss": TEST_ISSUER, "aud": TEST_AUDIENCE, "exp": now + 60, "roles": ["ADMIN"]}
    hs_token = jwt.encode(claims, "a-test-only-hmac-key-of-sufficient-length", algorithm="HS256", headers={"kid": "test-key-1"})
    none_token = jwt.encode(claims, None, algorithm="none", headers={"kid": "test-key-1"})
    for token in (hs_token, none_token):
        with pytest.raises(InvalidTokenError):
            make_test_verifier().verify(token)


def test_jwks_key_store_caches_and_refreshes_for_rotation():
    calls = []
    documents = [jwks_document(public_jwk()), jwks_document(public_jwk(), public_jwk(OTHER_KEY, kid="rotated"))]
    clock = {"now": 0.0}

    def fetch():
        calls.append(1)
        return documents[min(len(calls) - 1, 1)]

    store = JwksKeyStore(fetch, cache_ttl_seconds=300, clock=lambda: clock["now"])
    verifier = JwksTokenVerifier(store, TEST_ISSUER, TEST_AUDIENCE)

    verifier.verify(make_rs256_token())
    verifier.verify(make_rs256_token())
    assert len(calls) == 1  # cached

    rotated = make_rs256_token(key=OTHER_KEY, kid="rotated")
    with pytest.raises(InvalidTokenError):
        verifier.verify(rotated)  # unknown kid, refresh rate-limited
    assert len(calls) == 1

    clock["now"] = JwksKeyStore.MIN_REFRESH_INTERVAL_SECONDS
    assert verifier.verify(rotated).user_id == "usr-admin-001"
    assert len(calls) == 2


def test_jwks_fetch_failure_is_service_unavailable():
    def fetch():
        raise AppError(503, "IDENTITY_SERVICE_UNAVAILABLE", "keys unavailable")

    verifier = JwksTokenVerifier(JwksKeyStore(fetch), TEST_ISSUER, TEST_AUDIENCE)
    with pytest.raises(AppError) as exc_info:
        verifier.verify(make_rs256_token())
    assert exc_info.value.status_code == 503


def test_jwks_document_without_keys_is_service_unavailable():
    verifier = JwksTokenVerifier(JwksKeyStore(lambda: {"nope": []}), TEST_ISSUER, TEST_AUDIENCE)
    with pytest.raises(AppError) as exc_info:
        verifier.verify(make_rs256_token())
    assert exc_info.value.code == "IDENTITY_SERVICE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# HS256 verifier (current Identity Service compatibility mode)
# ---------------------------------------------------------------------------

HS_SECRET = "test-only-shared-secret-not-used-anywhere-else"


class FakeIdentityClient:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.forwarded = []

    def with_authorization(self, authorization):
        self.forwarded.append(authorization)
        return self

    def get_active_user(self, user_id):
        self.calls.append(user_id)
        if isinstance(self.result, AppError):
            raise self.result
        return self.result


def hs_token(sub="usr-admin-001", expires_in=300, secret=HS_SECRET, **extra):
    claims = {"sub": sub, "exp": int(time.time()) + expires_in, **extra}
    return jwt.encode(claims, secret, algorithm="HS256")


def test_hs256_verifier_takes_roles_from_identity_service():
    identity = FakeIdentityClient(IdentityUser("usr-admin-001", "ACTIVE", True, ("ADMIN",)))
    token = hs_token()
    principal = IdentityHs256TokenVerifier(HS_SECRET, identity).verify(token)
    assert principal.user_id == "usr-admin-001"
    assert principal.roles == frozenset({"ADMIN"})
    assert principal.roles_verified_live is True
    assert identity.calls == ["usr-admin-001"]
    assert identity.forwarded == [f"Bearer {token}"]


def test_hs256_verifier_ignores_roles_claim_in_token():
    identity = FakeIdentityClient(IdentityUser("usr-1", "ACTIVE", True, ("STUDENT",)))
    principal = IdentityHs256TokenVerifier(HS_SECRET, identity).verify(hs_token("usr-1", roles=["ADMIN"]))
    assert principal.roles == frozenset({"STUDENT"})


@pytest.mark.parametrize("token", [
    hs_token(secret="a-different-test-only-secret-value-xyz"),
    hs_token(expires_in=-60),
    jwt.encode({"exp": int(time.time()) + 60}, HS_SECRET, algorithm="HS256"),
    make_rs256_token(),
])
def test_hs256_verifier_rejects_invalid_tokens(token):
    identity = FakeIdentityClient(IdentityUser("usr-1", "ACTIVE", True, ("ADMIN",)))
    with pytest.raises(InvalidTokenError):
        IdentityHs256TokenVerifier(HS_SECRET, identity).verify(token)
    assert identity.calls == []


@pytest.mark.parametrize("code", ["USER_NOT_FOUND", "USER_INACTIVE"])
def test_hs256_verifier_rejects_unknown_or_inactive_subject(code):
    identity = FakeIdentityClient(AppError(404, code, "x"))
    with pytest.raises(InvalidTokenError):
        IdentityHs256TokenVerifier(HS_SECRET, identity).verify(hs_token())


def test_hs256_verifier_propagates_identity_outage():
    identity = FakeIdentityClient(AppError(503, "IDENTITY_SERVICE_UNAVAILABLE", "down"))
    with pytest.raises(AppError) as exc_info:
        IdentityHs256TokenVerifier(HS_SECRET, identity).verify(hs_token())
    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# Verifier selection from configuration
# ---------------------------------------------------------------------------

def test_default_mode_builds_jwks_verifier_with_contract_iss_and_aud():
    settings = load_settings({"IDENTITY_SERVICE_BASE_URL": "http://identity.test"})
    verifier = build_token_verifier(settings)
    assert isinstance(verifier, JwksTokenVerifier)
    assert verifier.issuer == "university-identity-service"
    assert verifier.audience == "university-services-platform"


def test_legacy_hs256_mode_builds_hs256_verifier():
    settings = load_settings({"AUTH_MODE": "identity-hs256", "JWT_SECRET_KEY": HS_SECRET,
                              "IDENTITY_SERVICE_BASE_URL": "http://identity.test"})
    assert isinstance(build_token_verifier(settings), IdentityHs256TokenVerifier)


def test_jwks_mode_uses_configured_issuer_and_audience():
    settings = load_settings({
        "AUTH_MODE": "jwks",
        "IDENTITY_SERVICE_BASE_URL": "http://identity.test",
        "JWT_ISSUER": TEST_ISSUER,
        "JWT_AUDIENCE": TEST_AUDIENCE,
    })
    verifier = build_token_verifier(settings)
    assert isinstance(verifier, JwksTokenVerifier)
    assert verifier.issuer == TEST_ISSUER


@pytest.mark.parametrize("env", [
    {},  # jwks (default) without IDENTITY_SERVICE_BASE_URL or JWKS_URL
    {"AUTH_MODE": "identity-hs256", "IDENTITY_SERVICE_BASE_URL": "http://identity.test"},  # no JWT_SECRET_KEY
])
def test_missing_configuration_fails_closed(env):
    with pytest.raises(AppError) as exc_info:
        build_token_verifier(load_settings(env))
    assert exc_info.value.code == "AUTH_NOT_CONFIGURED"
