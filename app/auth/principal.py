from dataclasses import dataclass
from typing import FrozenSet, Iterable

ADMIN_ROLE = "ADMIN"


@dataclass(frozen=True)
class Principal:
    """Authenticated caller, identical regardless of how the token was verified."""

    user_id: str
    roles: FrozenSet[str]

    @classmethod
    def build(cls, user_id: str, roles: Iterable[str]) -> "Principal":
        return cls(user_id=user_id, roles=frozenset(role.upper() for role in roles))

    def has_any_role(self, roles: Iterable[str]) -> bool:
        return bool(self.roles & {role.upper() for role in roles})
