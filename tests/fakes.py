"""Test doubles for external services."""
from typing import Dict, Iterable, List, Optional

from app.core.errors import AppError
from app.integrations.identity_client import IdentityUser, user_inactive


class FakeIdentityClient:
    """Stands in for the Identity Service (API contract v1). Synthetic users only.

    Every user exists and is ACTIVE with role STAFF unless a test configures otherwise.
    `aliases` maps a university id to the canonical user id, as the real service does.
    `calls` records target-user checks (get_active_user), `lookups` records existence
    checks (lookup_user), and `role_checks` records live role confirmations for the caller.
    """

    def __init__(self):
        self.missing: set = set()
        self.inactive: set = set()
        self.roles: Dict[str, Iterable[str]] = {}
        self.aliases: Dict[str, str] = {}
        self.outage: Optional[AppError] = None
        self.calls: List[str] = []
        self.lookups: List[str] = []
        self.role_checks: List[tuple] = []

    def with_authorization(self, authorization):
        return self

    def _resolve(self, user_id: str) -> IdentityUser:
        if self.outage is not None:
            raise self.outage
        if user_id in self.missing:
            raise AppError(404, "USER_NOT_FOUND", f"User '{user_id}' was not found in the Identity Service.")
        canonical = self.aliases.get(user_id, user_id)
        active = canonical not in self.inactive
        roles = tuple(r.upper() for r in self.roles.get(canonical, ("STAFF",)))
        return IdentityUser(canonical, "ACTIVE" if active else "INACTIVE", active, roles)

    def lookup_user(self, user_id: str, required_role: Optional[str] = None) -> IdentityUser:
        if required_role:
            self.role_checks.append((user_id, required_role))
        else:
            self.lookups.append(user_id)
        user = self._resolve(user_id)
        if required_role:
            user = IdentityUser(user.user_id, user.status, user.is_active, user.roles,
                                is_authorized=required_role.upper() in user.roles)
        return user

    def get_active_user(self, user_id: str) -> IdentityUser:
        self.calls.append(user_id)
        user = self._resolve(user_id)
        if not user.is_active:
            raise user_inactive(user.user_id)
        return user

    def go_down(self) -> None:
        self.outage = AppError(
            503,
            "IDENTITY_SERVICE_UNAVAILABLE",
            "The Identity Service is currently unavailable. Please retry later.",
        )
