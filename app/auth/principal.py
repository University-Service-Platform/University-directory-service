from dataclasses import dataclass
from typing import FrozenSet, Iterable

ADMIN_ROLE = "ADMIN"


@dataclass(frozen=True)
class Principal:
    """Authenticated caller, identical regardless of how the token was verified."""

    user_id: str
    roles: FrozenSet[str]
    # True when roles were read live from the Identity Service; False when they are the
    # login-time snapshot carried in the token (must be re-confirmed before protected actions).
    roles_verified_live: bool = False

    @classmethod
    def build(cls, user_id: str, roles: Iterable[str], roles_verified_live: bool = False) -> "Principal":
        return cls(
            user_id=user_id,
            roles=frozenset(role.upper() for role in roles),
            roles_verified_live=roles_verified_live,
        )

    def has_any_role(self, roles: Iterable[str]) -> bool:
        return bool(self.roles & {role.upper() for role in roles})
