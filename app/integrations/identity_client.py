"""HTTP client for the Identity Service (Identity API contract v1).

The Directory Service never reads the Identity database. It asks the Identity
Service's user validation endpoint:

    GET {IDENTITY_SERVICE_BASE_URL}/api/v1/validation/users/{user_id}[?required_role=R]

The v1 endpoint requires the bearer token of an active user, so the caller's
Authorization header is forwarded. `require_active` is deliberately not sent:
an inactive *target* user is then reported in the body (`is_valid: false`),
and a 403 ACCOUNT_INACTIVE can only mean the *caller's* account is inactive.

Downstream failures are mapped to Directory Service errors; downstream error
text is logged, never returned to clients.
"""
import logging
from dataclasses import dataclass, replace
from typing import Any, Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import Request, status

from app.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

VALIDATION_PATH = "/api/v1/validation/users/{user_id}"

IDENTITY_SERVICE_UNAVAILABLE = "IDENTITY_SERVICE_UNAVAILABLE"
IDENTITY_SERVICE_ERROR = "IDENTITY_SERVICE_ERROR"
IDENTITY_SERVICE_BAD_RESPONSE = "IDENTITY_SERVICE_BAD_RESPONSE"
USER_NOT_FOUND = "USER_NOT_FOUND"
USER_INACTIVE = "USER_INACTIVE"


@dataclass(frozen=True)
class IdentityUser:
    user_id: str  # canonical Identity user id (the JWT `sub`), even if looked up by university id
    status: str
    is_active: bool
    roles: Tuple[str, ...]
    is_authorized: bool = True  # False only when a required_role was checked and not held


def _unavailable() -> AppError:
    return AppError(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        IDENTITY_SERVICE_UNAVAILABLE,
        "The Identity Service is currently unavailable. Please retry later.",
    )


def _downstream_error() -> AppError:
    return AppError(
        status.HTTP_502_BAD_GATEWAY,
        IDENTITY_SERVICE_ERROR,
        "The Identity Service returned an error.",
    )


def _bad_response() -> AppError:
    return AppError(
        status.HTTP_502_BAD_GATEWAY,
        IDENTITY_SERVICE_BAD_RESPONSE,
        "The Identity Service returned an unexpected response.",
    )


def user_inactive(user_id: str) -> AppError:
    return AppError(
        status.HTTP_409_CONFLICT,
        USER_INACTIVE,
        f"User '{user_id}' is not active in the Identity Service.",
    )


def _error_code(response: httpx.Response) -> Optional[str]:
    try:
        body = response.json()
    except ValueError:
        return None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        code = body["error"].get("code")
        return code if isinstance(code, str) else None
    return None


def _parse_user(response: httpx.Response) -> IdentityUser:
    try:
        body: Any = response.json()
    except ValueError:
        logger.warning("Identity Service returned non-JSON body (status %s)", response.status_code)
        raise _bad_response()

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        logger.warning("Identity Service response is missing 'data'")
        raise _bad_response()

    user_id = data.get("user_id")
    account_status = data.get("status")
    is_valid = data.get("is_valid")
    roles = data.get("roles", [])
    is_authorized = data.get("is_authorized", True)
    if (
        not isinstance(user_id, str)
        or not isinstance(account_status, str)
        or not isinstance(is_valid, bool)
        or not isinstance(is_authorized, bool)
        or not isinstance(roles, list)
        or not all(isinstance(role, str) for role in roles)
    ):
        logger.warning("Identity Service response has unexpected field types")
        raise _bad_response()

    return IdentityUser(
        user_id=user_id,
        status=account_status.upper(),
        is_active=is_valid and account_status.upper() == "ACTIVE",
        roles=tuple(role.upper() for role in roles),
        is_authorized=is_authorized,
    )


@dataclass(frozen=True)
class IdentityClient:
    base_url: Optional[str]
    connect_timeout: float
    read_timeout: float
    authorization: Optional[str] = None  # caller's "Bearer <token>", forwarded as-is
    transport: Optional[httpx.BaseTransport] = None

    def __post_init__(self):
        if self.base_url:
            object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    @property
    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout, read=self.read_timeout, write=self.read_timeout, pool=self.connect_timeout
        )

    def with_authorization(self, authorization: Optional[str]) -> "IdentityClient":
        return replace(self, authorization=authorization)

    def lookup_user(self, user_id: str, required_role: Optional[str] = None) -> IdentityUser:
        """Return the user's status and roles. Raises a mapped AppError if the user or the call fails."""
        if not self.base_url:
            logger.error("IDENTITY_SERVICE_BASE_URL is not configured")
            raise _unavailable()

        path = VALIDATION_PATH.format(user_id=quote(user_id, safe=""))
        params = {"required_role": required_role} if required_role else None
        headers = {"Authorization": self.authorization} if self.authorization else None
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=self.transport) as client:
                response = client.get(path, params=params, headers=headers)
        except httpx.TimeoutException:
            logger.warning("Identity Service request timed out")
            raise _unavailable()
        except httpx.TransportError as exc:
            logger.warning("Identity Service connection failed: %s", type(exc).__name__)
            raise _unavailable()

        if response.status_code == status.HTTP_200_OK:
            return _parse_user(response)

        code = _error_code(response)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                USER_NOT_FOUND,
                f"User '{user_id}' was not found in the Identity Service.",
            )
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            # The forwarded caller token was rejected by the Identity Service.
            raise AppError(
                status.HTTP_401_UNAUTHORIZED,
                "UNAUTHORIZED",
                "The Identity Service did not accept the caller's credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if response.status_code == status.HTTP_403_FORBIDDEN and code == "ACCOUNT_INACTIVE":
            # require_active is never sent, so this refers to the caller, not the target user.
            raise AppError(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Your account is not active.")

        logger.warning("Identity Service responded with status %s (code %s)", response.status_code, code)
        raise _downstream_error()

    def get_active_user(self, user_id: str) -> IdentityUser:
        """Return the user if it exists and is ACTIVE; otherwise raise USER_NOT_FOUND / USER_INACTIVE."""
        user = self.lookup_user(user_id)
        if not user.is_active:
            raise user_inactive(user.user_id)
        return user


def get_identity_client(request: Request) -> IdentityClient:
    """FastAPI dependency: an Identity client that forwards the current request's credentials.

    Override in tests with a fake client.
    """
    settings = get_settings()
    return IdentityClient(
        base_url=settings.identity_service_base_url,
        connect_timeout=settings.identity_timeout_connect,
        read_timeout=settings.identity_timeout_read,
        authorization=request.headers.get("Authorization"),
    )
