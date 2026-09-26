"""Test-only token helpers. Keys are generated in memory for each test run; nothing is stored."""
import time
from typing import Any, Dict, Iterable, Optional

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.verifiers import JwksKeyStore, JwksTokenVerifier

TEST_ISSUER = "test-identity-issuer"
TEST_AUDIENCE = "test-directory-audience"
TEST_KID = "test-key-1"

SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def public_jwk(private_key=SIGNING_KEY, kid: str = TEST_KID) -> Dict[str, Any]:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return jwk


def jwks_document(*jwks: Dict[str, Any]) -> Dict[str, Any]:
    return {"keys": list(jwks) or [public_jwk()]}


def make_rs256_token(
    sub: str = "usr-admin-001",
    roles: Optional[Iterable[str]] = ("ADMIN",),
    *,
    key=SIGNING_KEY,
    kid: str = TEST_KID,
    issuer: str = TEST_ISSUER,
    audience: str = TEST_AUDIENCE,
    expires_in: int = 300,
    extra: Optional[Dict[str, Any]] = None,
    drop: Iterable[str] = (),
) -> str:
    now = int(time.time())
    claims: Dict[str, Any] = {"sub": sub, "iss": issuer, "aud": audience, "iat": now, "exp": now + expires_in}
    if roles is not None:
        claims["roles"] = list(roles)
    claims.update(extra or {})
    for name in drop:
        claims.pop(name, None)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def make_test_verifier(document: Optional[Dict[str, Any]] = None) -> JwksTokenVerifier:
    """JWKS verifier backed by an in-memory key set (mocked JWKS endpoint, no network)."""
    store = JwksKeyStore(lambda: document or jwks_document())
    return JwksTokenVerifier(store, issuer=TEST_ISSUER, audience=TEST_AUDIENCE)


def bearer(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


ADMIN_TOKEN = make_rs256_token("usr-admin-001", ["ADMIN"])
STAFF_TOKEN = make_rs256_token("usr-staff-001", ["STAFF"])
