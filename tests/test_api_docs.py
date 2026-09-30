"""Keep docs/API_CONTRACT.md honest: it must list every implemented operation and every error code."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
OPENAPI = json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))

# Codes that appear as string literals in app/ but are never returned by this API's routes.
NOT_ERROR_CODES = {
    "ACTIVE", "INACTIVE", "ADMIN", "STAFF",  # statuses / roles
    "ACCOUNT_INACTIVE",                      # Identity Service's code, only read, never returned
    "RESTRICT",                              # SQL ON DELETE rule
    "BAD_REQUEST", "CONFLICT", "HTTP_ERROR", # generic fallbacks for framework HTTPExceptions no route raises
}


def _section(title: str) -> str:
    return CONTRACT.split(title, 1)[1].split("\n## ", 1)[0]


def test_endpoint_summary_matches_openapi():
    summary = _section("## Endpoint summary")
    documented = set(re.findall(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \|", summary, re.M))
    implemented = {(m.upper(), p) for p, ops in OPENAPI["paths"].items() for m in ops}
    assert documented == implemented, {
        "missing from docs": sorted(implemented - documented),
        "documented but not implemented": sorted(documented - implemented),
    }


ERROR_CODE_PATTERNS = [
    r'(?:AppError|api_error)\(\s*[^,()]+,\s*"([A-Z_]+)"',   # AppError(status, "CODE", ...)
    r'error_body\(\s*"([A-Z_]+)"',                           # error_body("CODE", ...)
    r'ensure_no_dependencies\(\s*"([A-Z_]+)"',               # delete protection codes
    r'^\s*[A-Z_]+ = "([A-Z_]+)"\s*$',                        # CODE constants
    r'\b\d{3}: "([A-Z_]+)"',                                 # status -> code map
]


def returned_error_codes():
    codes = set()
    for source in (ROOT / "app").rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        for pattern in ERROR_CODE_PATTERNS:
            codes |= set(re.findall(pattern, text, re.M))
    return codes - NOT_ERROR_CODES


def test_error_code_scan_finds_the_known_codes():
    codes = returned_error_codes()
    assert {"VALIDATION_ERROR", "UNAUTHORIZED", "FACULTY_HAS_DEPENDENCIES", "USER_INACTIVE",
            "IDENTITY_SERVICE_UNAVAILABLE", "AUTH_NOT_CONFIGURED", "METHOD_NOT_ALLOWED"} <= codes


def test_every_error_code_is_in_the_error_index():
    index = _section("## 4. Error code index")
    missing = sorted(code for code in returned_error_codes() if f"`{code}`" not in index)
    assert not missing, f"error codes missing from docs/API_CONTRACT.md section 4: {missing}"
