"""HTTP client for the Identity Service.

The Directory Service never reads the Identity database. It asks the Identity
Service's existing validation endpoint:

    GET {IDENTITY_SERVICE_BASE_URL}/validation/users/{user_id}?require_active=true

Downstream failures are mapped to Directory Service errors; downstream error
text is logged, never returned to clients.
"""
import logging
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import status

from app.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

VALIDATION_PATH = "/validation/users/{user_id}"

IDENTITY_SERVICE_UNAVAILABLE = "IDENTITY_SERVICE_UNAVAILABLE"
IDENTITY_SERVICE_ERROR = "IDENTITY_SERVICE_ERROR"
IDENTITY_SERVICE_BAD_RESPONSE = "IDENTITY_SERVICE_BAD_RESPONSE"
USER_NOT_FOUND = "USER_NOT_FOUND"
USER_INACTIVE = "USER_INACTIVE"


@dataclass(frozen=True)
class IdentityUser:
    user_id: str
    status: str
    roles: Tuple[str, ...]


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


def _user_inactive(user_id: str) -> AppError:
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
    if (
        not isinstance(user_id, str)
        or not isinstance(account_status, str)
        or not isinstance(is_valid, bool)
        or not isinstance(roles, list)
        or not all(isinstance(role, str) for role in roles)
    ):
        logger.warning("Identity Service response has unexpected field types")
        raise _bad_response()

    if not is_valid or account_status.upper() != "ACTIVE":
        raise _user_inactive(user_id)

    return IdentityUser(
        user_id=user_id,
        status=account_status.upper(),
        roles=tuple(role.upper() for role in roles),
    )


class IdentityClient:
    def __init__(
        self,
        base_url: Optional[str],
        connect_timeout: float,
        read_timeout: float,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = httpx.Timeout(
            connect=connect_timeout, read=read_timeout, write=read_timeout, pool=connect_timeout
        )
        self.transport = transport

    def get_active_user(self, user_id: str) -> IdentityUser:
        """Return the user if it exists and is ACTIVE; otherwise raise a mapped AppError."""
        if not self.base_url:
            logger.error("IDENTITY_SERVICE_BASE_URL is not configured")
            raise _unavailable()

        path = VALIDATION_PATH.format(user_id=quote(user_id, safe=""))
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=self.transport) as client:
                response = client.get(path, params={"require_active": "true"})
        except httpx.TimeoutException:
            logger.warning("Identity Service request timed out")
            raise _unavailable()
        except httpx.TransportError as exc:
            logger.warning("Identity Service connection failed: %s", type(exc).__name__)
            raise _unavailable()

        if response.status_code == status.HTTP_200_OK:
            return _parse_user(response)

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                USER_NOT_FOUND,
                f"User '{user_id}' was not found in the Identity Service.",
            )

        if response.status_code == status.HTTP_403_FORBIDDEN and _error_code(response) == "ACCOUNT_INACTIVE":
            raise _user_inactive(user_id)

        logger.warning("Identity Service responded with status %s", response.status_code)
        raise _downstream_error()


def get_identity_client() -> IdentityClient:
    """FastAPI dependency; override in tests with a fake client."""
    settings = get_settings()
    return IdentityClient(
        base_url=settings.identity_service_base_url,
        connect_timeout=settings.identity_timeout_connect,
        read_timeout=settings.identity_timeout_read,
    )
