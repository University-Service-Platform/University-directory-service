import logging
from functools import lru_cache
from typing import Callable, Optional

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.principal import ADMIN_ROLE, Principal
from app.auth.verifiers import (
    IdentityHs256TokenVerifier,
    InvalidTokenError,
    JwksKeyStore,
    JwksTokenVerifier,
    TokenVerifier,
    http_jwks_fetcher,
)
from app.config import AUTH_MODE_JWKS, Settings, get_settings
from app.core.errors import AppError
from app.integrations.identity_client import IdentityClient

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False, description="JWT issued by the Identity Service")


def _unauthorized(message: str) -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "UNAUTHORIZED",
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _not_configured(reason: str) -> AppError:
    logger.error("Authentication is not configured: %s", reason)
    return AppError(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AUTH_NOT_CONFIGURED",
        "Authentication is not configured on this service.",
    )


def build_token_verifier(settings: Settings) -> TokenVerifier:
    """Select the verifier for AUTH_MODE. Both produce the same Principal."""
    identity_client = IdentityClient(
        settings.identity_service_base_url,
        connect_timeout=settings.identity_timeout_connect,
        read_timeout=settings.identity_timeout_read,
    )

    if settings.auth_mode == AUTH_MODE_JWKS:
        jwks_url = settings.resolved_jwks_url
        if not (jwks_url and settings.jwt_issuer and settings.jwt_audience):
            raise _not_configured(
                "jwks mode needs JWT_ISSUER, JWT_AUDIENCE and JWKS_URL or IDENTITY_SERVICE_BASE_URL"
            )
        key_store = JwksKeyStore(
            http_jwks_fetcher(jwks_url, identity_client.timeout), settings.jwks_cache_ttl_seconds
        )
        return JwksTokenVerifier(key_store, issuer=settings.jwt_issuer, audience=settings.jwt_audience)

    if not settings.jwt_secret_key:
        raise _not_configured("identity-hs256 mode needs JWT_SECRET_KEY")
    return IdentityHs256TokenVerifier(settings.jwt_secret_key, identity_client)


@lru_cache
def _cached_verifier(settings: Settings) -> TokenVerifier:
    return build_token_verifier(settings)


def get_token_verifier() -> TokenVerifier:
    """FastAPI dependency; cached so the JWKS cache survives across requests."""
    return _cached_verifier(get_settings())


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Authentication credentials were not provided.")
    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError as exc:
        raise _unauthorized(str(exc))


def require_roles(*roles: str) -> Callable[..., Principal]:
    required = tuple(role.upper() for role in roles)

    def dependency(principal: Principal = Depends(get_current_user)) -> Principal:
        if not principal.has_any_role(required):
            raise AppError(
                status.HTTP_403_FORBIDDEN,
                "FORBIDDEN",
                f"This operation requires one of the roles: {', '.join(required)}.",
            )
        return principal

    return dependency


require_admin = require_roles(ADMIN_ROLE)
