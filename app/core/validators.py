import re
from typing import Optional

from fastapi import status

from app.core.errors import AppError

IDENTIFIER_PATTERN = re.compile(r"[a-zA-Z0-9_-]{2,50}")
CODE_PATTERN = re.compile(r"[a-zA-Z0-9_-]{2,20}")

INVALID_IDENTIFIER_FORMAT = "INVALID_IDENTIFIER_FORMAT"


def is_valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(IDENTIFIER_PATTERN.fullmatch(value.strip()))


def is_valid_code(value: object) -> bool:
    return isinstance(value, str) and bool(CODE_PATTERN.fullmatch(value.strip()))


def ensure_identifier(value: str, label: str) -> str:
    """Raise 400 INVALID_IDENTIFIER_FORMAT unless value is a valid identifier; return it stripped."""
    if not is_valid_identifier(value):
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            INVALID_IDENTIFIER_FORMAT,
            f"{label} identifier '{value}' has an invalid format.",
        )
    return value.strip()


def ensure_code(value: str, label: str, display: Optional[str] = None) -> str:
    """Raise 400 INVALID_IDENTIFIER_FORMAT unless value is a valid code; return it stripped."""
    if not is_valid_code(value):
        shown = value if display is None else display
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            INVALID_IDENTIFIER_FORMAT,
            f"{label} code '{shown}' has an invalid format.",
        )
    return value.strip()
