"""Token verifiers. Each one turns a bearer token into the same Principal.

- JwksTokenVerifier (AUTH_MODE=jwks, default): Identity API contract v1.
  RS256 signature checked against the Identity Service JWKS; iss, aud, exp and
  sub required; roles read from the token's "roles" claim (a login-time
  snapshot, re-confirmed live before protected actions).
- IdentityHs256TokenVerifier (AUTH_MODE=identity-hs256, legacy): the Sprint 1
  Identity Service, which signed HS256 tokens with a shared JWT_SECRET_KEY and
  put no roles, iss or aud in them. Signature and exp are checked locally; the
  subject's status and roles come live from the Identity validation endpoint.
"""
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Protocol

import httpx
import jwt
from fastapi import status

from app.auth.principal import Principal
from app.core.errors import AppError
from app.integrations.identity_client import IdentityClient

logger = logging.getLogger(__name__)

INVALID_TOKEN_MESSAGE = "Authentication token is invalid."


class InvalidTokenError(Exception):
    """Token rejected. The message is safe to return to clients."""


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal:
        ...


def _decode_error_message(exc: jwt.PyJWTError) -> str:
    if isinstance(exc, jwt.ExpiredSignatureError):
        return "Authentication token has expired."
    return INVALID_TOKEN_MESSAGE


def _require_subject(claims: Dict[str, Any]) -> str:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise InvalidTokenError(INVALID_TOKEN_MESSAGE)
    return subject.strip()


# ---------------------------------------------------------------------------
# RS256 + JWKS (target contract)
# ---------------------------------------------------------------------------

def _keys_unavailable() -> AppError:
    return AppError(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "IDENTITY_SERVICE_UNAVAILABLE",
        "Token signing keys are currently unavailable. Please retry later.",
    )


def http_jwks_fetcher(jwks_url: str, timeout: httpx.Timeout) -> Callable[[], Dict[str, Any]]:
    def fetch() -> Dict[str, Any]:
        try:
            response = httpx.get(jwks_url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Fetching JWKS failed: %s", type(exc).__name__)
            raise _keys_unavailable()
    return fetch


class JwksKeyStore:
    """Caches the JWKS; refetches after the TTL or (rate-limited) on an unknown kid."""

    MIN_REFRESH_INTERVAL_SECONDS = 10.0

    def __init__(
        self,
        fetch_jwks: Callable[[], Dict[str, Any]],
        cache_ttl_seconds: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._fetch = fetch_jwks
        self._ttl = cache_ttl_seconds
        self._clock = clock
        self._keys: Optional[Dict[str, Any]] = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def get_signing_key(self, kid: str) -> Optional[Any]:
        with self._lock:
            now = self._clock()
            if self._keys is None or now - self._fetched_at >= self._ttl:
                self._refresh(now)
            elif kid not in self._keys and now - self._fetched_at >= self.MIN_REFRESH_INTERVAL_SECONDS:
                self._refresh(now)  # key rotation
            return self._keys.get(kid)

    def _refresh(self, now: float) -> None:
        document = self._fetch()
        entries = document.get("keys") if isinstance(document, dict) else None
        if not isinstance(entries, list):
            logger.warning("JWKS document has no 'keys' list")
            raise _keys_unavailable()

        keys: Dict[str, Any] = {}
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("kty") != "RSA" or not entry.get("kid"):
                continue
            if entry.get("use") not in (None, "sig"):
                continue
            try:
                keys[entry["kid"]] = jwt.PyJWK(entry, algorithm="RS256").key
            except jwt.PyJWTError:
                logger.warning("Skipping unusable JWKS entry kid=%s", entry.get("kid"))
        self._keys = keys
        self._fetched_at = now


class JwksTokenVerifier:
    ALGORITHM = "RS256"

    def __init__(self, key_store: JwksKeyStore, issuer: str, audience: str):
        self.key_store = key_store
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise InvalidTokenError(INVALID_TOKEN_MESSAGE)

        if header.get("alg") != self.ALGORITHM or not isinstance(header.get("kid"), str):
            raise InvalidTokenError(INVALID_TOKEN_MESSAGE)

        key = self.key_store.get_signing_key(header["kid"])
        if key is None:
            raise InvalidTokenError(INVALID_TOKEN_MESSAGE)

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[self.ALGORITHM],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(_decode_error_message(exc))

        roles = claims.get("roles", [])
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise InvalidTokenError(INVALID_TOKEN_MESSAGE)

        return Principal.build(_require_subject(claims), roles)


# ---------------------------------------------------------------------------
# HS256 + Identity role lookup (current Identity Service)
# ---------------------------------------------------------------------------

class IdentityHs256TokenVerifier:
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, identity_client: IdentityClient):
        self._secret_key = secret_key
        self.identity_client = identity_client

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self.ALGORITHM],
                options={"require": ["exp", "sub"], "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(_decode_error_message(exc))

        subject = _require_subject(claims)
        try:
            user = self.identity_client.with_authorization(f"Bearer {token}").get_active_user(subject)
        except AppError as exc:
            if exc.code in ("USER_NOT_FOUND", "USER_INACTIVE", "UNAUTHORIZED", "FORBIDDEN"):
                raise InvalidTokenError("Authentication token subject is not an active user.")
            raise  # Identity Service unavailable/error: surfaced as 503/502

        return Principal.build(subject, user.roles, roles_verified_live=True)
