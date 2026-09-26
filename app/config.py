import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping, Optional

AUTH_MODE_IDENTITY_HS256 = "identity-hs256"
AUTH_MODE_JWKS = "jwks"
SUPPORTED_AUTH_MODES = (AUTH_MODE_IDENTITY_HS256, AUTH_MODE_JWKS)

DEFAULT_DATABASE_URL = "sqlite:///./directory.db"
JWKS_PATH = "/.well-known/jwks.json"


class ConfigurationError(ValueError):
    """Raised when an environment variable holds an unusable value."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    identity_service_base_url: Optional[str]
    identity_timeout_connect: float
    identity_timeout_read: float
    auth_mode: str
    jwt_secret_key: Optional[str]
    jwt_issuer: Optional[str]
    jwt_audience: Optional[str]
    jwks_url: Optional[str]
    jwks_cache_ttl_seconds: int

    @property
    def resolved_jwks_url(self) -> Optional[str]:
        """Explicit JWKS_URL, otherwise derived from the Identity Service base URL."""
        if self.jwks_url:
            return self.jwks_url
        if self.identity_service_base_url:
            return f"{self.identity_service_base_url}{JWKS_PATH}"
        return None


def _optional(env: Mapping[str, str], name: str) -> Optional[str]:
    value = env.get(name, "").strip()
    return value or None


def _positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be a number.")
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env

    auth_mode = (_optional(env, "AUTH_MODE") or AUTH_MODE_IDENTITY_HS256).lower()
    if auth_mode not in SUPPORTED_AUTH_MODES:
        raise ConfigurationError(
            f"AUTH_MODE must be one of: {', '.join(SUPPORTED_AUTH_MODES)}."
        )

    base_url = _optional(env, "IDENTITY_SERVICE_BASE_URL")
    if base_url:
        base_url = base_url.rstrip("/")

    return Settings(
        database_url=_optional(env, "DATABASE_URL") or DEFAULT_DATABASE_URL,
        identity_service_base_url=base_url,
        identity_timeout_connect=_positive_float(env, "IDENTITY_TIMEOUT_CONNECT", 3.0),
        identity_timeout_read=_positive_float(env, "IDENTITY_TIMEOUT_READ", 5.0),
        auth_mode=auth_mode,
        jwt_secret_key=_optional(env, "JWT_SECRET_KEY"),
        jwt_issuer=_optional(env, "JWT_ISSUER"),
        jwt_audience=_optional(env, "JWT_AUDIENCE"),
        jwks_url=_optional(env, "JWKS_URL"),
        jwks_cache_ttl_seconds=int(_positive_float(env, "JWKS_CACHE_TTL_SECONDS", 300)),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
