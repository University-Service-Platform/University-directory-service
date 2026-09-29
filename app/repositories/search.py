from typing import Optional

from sqlalchemy import or_


def normalise_query(q: Optional[str]) -> Optional[str]:
    """Trim a free-text search term; blank means "no search"."""
    if q is None:
        return None
    q = q.strip()
    return q or None


def contains_any(q: str, *columns):
    """Case-insensitive substring match on any column. % and _ in the term are matched literally."""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    return or_(*(column.ilike(pattern, escape="\\") for column in columns))
