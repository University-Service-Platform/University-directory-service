"""Test doubles for external services."""
from typing import Dict, Iterable, List, Optional

from app.core.errors import AppError
from app.integrations.identity_client import IdentityUser


class FakeIdentityClient:
    """Stands in for the Identity Service. Every user is ACTIVE unless configured otherwise."""

    def __init__(self):
        self.missing: set = set()
        self.inactive: set = set()
        self.roles: Dict[str, Iterable[str]] = {}
        self.outage: Optional[AppError] = None
        self.calls: List[str] = []

    def get_active_user(self, user_id: str) -> IdentityUser:
        self.calls.append(user_id)
        if self.outage is not None:
            raise self.outage
        if user_id in self.missing:
            raise AppError(404, "USER_NOT_FOUND", f"User '{user_id}' was not found in the Identity Service.")
        if user_id in self.inactive:
            raise AppError(409, "USER_INACTIVE", f"User '{user_id}' is not active in the Identity Service.")
        return IdentityUser(user_id=user_id, status="ACTIVE", roles=tuple(self.roles.get(user_id, ("STAFF",))))

    def go_down(self) -> None:
        self.outage = AppError(
            503,
            "IDENTITY_SERVICE_UNAVAILABLE",
            "The Identity Service is currently unavailable. Please retry later.",
        )
