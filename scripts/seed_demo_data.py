"""Load synthetic demo data into a running Directory Service, through its public API.

All data is SYNTHETIC. It is built around the Identity Service's synthetic demo users
(ADM001, STF001, STU001, ACD001, ADS001, SDO001, TEC001, RMG001, EVO001) so that
Groups 6-8 can exercise their workflows against the hosted services.

Every record goes through the normal API: an ADMIN logs in at the Identity Service, and the
Directory Service verifies each user with the Identity Service before storing it. The script
is idempotent: records that already exist are skipped, so it is safe to run more than once.

Usage (the admin password is never passed on the command line or stored):

    # PowerShell
    $env:SEED_ADMIN_PASSWORD = "<demo admin password>"
    python scripts/seed_demo_data.py --base-url https://<api-gateway>

    # or call the services directly instead of through the gateway
    python scripts/seed_demo_data.py --identity-url https://<identity> --directory-url https://<directory>

If SEED_ADMIN_PASSWORD is not set, the script asks for the password.
"""
import argparse
import getpass
import os
import sys
from typing import Callable, Dict, List, Tuple

import httpx

SYNTHETIC = "Synthetic demo data"

FACULTIES: List[Tuple[str, str]] = [
    ("FSC", "Faculty of Science"),
    ("FCT", "Faculty of Computing and Technology"),
    ("FHS", "Faculty of Humanities and Social Sciences"),
]

DEPARTMENTS: List[Tuple[str, str, str]] = [  # code, name, faculty code
    ("CS", "Department of Computer Science", "FSC"),
    ("MATH", "Department of Mathematics", "FSC"),
    ("SE", "Department of Software Engineering", "FCT"),
    ("ENG", "Department of English", "FHS"),
]

SERVICE_UNITS: List[Tuple[str, str]] = [
    ("ITHD", "IT Help Desk"),
    ("FMU", "Facilities Management Unit"),
    ("RES", "Resource Booking Office"),
    ("EVT", "Events Office"),
    ("LIB", "Library Services"),
]

# University id of an Identity demo user -> department code. STU002 is inactive in the
# Identity Service and is deliberately not affiliated (it demonstrates rejection).
AFFILIATIONS: List[Tuple[str, str]] = [
    ("STU001", "CS"),
    ("ACD001", "CS"),
    ("STF001", "MATH"),
    ("ADS001", "SE"),
]

# University id, organisational scope (codes), role title.
RESPONSIBILITIES: List[Tuple[str, Dict[str, str], str]] = [
    ("SDO001", {"service_unit_id": "ITHD"}, "Service Desk Lead"),
    ("TEC001", {"service_unit_id": "ITHD"}, "IT Support Technician"),
    ("TEC001", {"service_unit_id": "FMU"}, "Maintenance Technician"),
    ("RMG001", {"service_unit_id": "RES"}, "Resource Booking Manager"),
    ("RMG001", {"department_id": "CS"}, "Department Resource Manager"),
    ("EVO001", {"service_unit_id": "EVT"}, "Event Coordinator"),
    ("ADS001", {"service_unit_id": "LIB"}, "Library Administrator"),
    ("ACD001", {"department_id": "CS", "faculty_id": "FSC"}, "Head of Department"),
]


class SeedError(RuntimeError):
    pass


def _fail(what: str, response: httpx.Response) -> SeedError:
    try:
        error = response.json().get("error", {})
        detail = f"{error.get('code')}: {error.get('message')}"
    except ValueError:
        detail = response.text[:200]
    return SeedError(f"{what} failed with HTTP {response.status_code} ({detail})")


def _error_code(response: httpx.Response) -> str:
    try:
        return response.json().get("error", {}).get("code", "")
    except ValueError:
        return ""


def seed(directory: httpx.Client, headers: Dict[str, str], log: Callable[[str], None] = print) -> Dict[str, int]:
    """Create the demo records that do not exist yet. Returns counts of created and skipped records."""
    counts = {"created": 0, "skipped": 0}

    def created(label: str) -> None:
        counts["created"] += 1
        log(f"  created  {label}")

    def skipped(label: str) -> None:
        counts["skipped"] += 1
        log(f"  exists   {label}")

    def ensure(kind: str, validate_path: str, create_path: str, body: Dict[str, str], label: str) -> None:
        check = directory.get(validate_path, headers=headers)
        if check.status_code == 200:
            return skipped(label)
        if check.status_code != 404:
            raise _fail(f"checking {kind} {label}", check)
        response = directory.post(create_path, json=body, headers=headers)
        if response.status_code != 201:
            raise _fail(f"creating {kind} {label}", response)
        created(label)

    log("Faculties")
    for code, name in FACULTIES:
        ensure("faculty", f"/api/v1/validation/faculties/{code}", "/api/v1/faculties",
               {"code": code, "name": name, "description": SYNTHETIC}, f"{code} {name}")

    log("Departments")
    for code, name, faculty in DEPARTMENTS:
        ensure("department", f"/api/v1/validation/departments/{code}", "/api/v1/departments",
               {"code": code, "name": name, "faculty_id": faculty}, f"{code} {name} ({faculty})")

    log("Service units")
    for code, name in SERVICE_UNITS:
        ensure("service unit", f"/api/v1/validation/service-units/{code}", "/api/v1/service-units",
               {"code": code, "name": name, "description": SYNTHETIC}, f"{code} {name}")

    log("Affiliations")
    for user, department in AFFILIATIONS:
        label = f"{user} -> {department}"
        response = directory.post("/api/v1/affiliations", json={"user_id": user, "department_id": department},
                                  headers=headers)
        if response.status_code == 201:
            created(label)
        elif response.status_code == 409 and _error_code(response) == "AFFILIATION_ALREADY_EXISTS":
            skipped(label)
        else:
            raise _fail(f"creating affiliation {label}", response)

    log("Service responsibilities")
    for user, scope, title in RESPONSIBILITIES:
        label = f"{user} {title} @ {', '.join(scope.values())}"
        response = directory.post("/api/v1/responsibilities", json={"user_id": user, "role_title": title, **scope},
                                  headers=headers)
        if response.status_code == 201:
            created(label)
        elif response.status_code == 409 and _error_code(response) == "RESPONSIBILITY_ALREADY_EXISTS":
            skipped(label)
        else:
            raise _fail(f"creating responsibility {label}", response)

    return counts


def login(identity: httpx.Client, username: str, password: str) -> Dict[str, str]:
    response = identity.post("/api/v1/auth/login", json={"username": username, "password": password})
    if response.status_code != 200:
        raise _fail(f"login as {username}", response)
    data = response.json()["data"]
    if "ADMIN" not in [role.upper() for role in data.get("roles", [])]:
        raise SeedError(f"{username} does not hold the ADMIN role")
    return {"Authorization": f"Bearer {data['access_token']}"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Load synthetic demo data into the Directory Service.")
    parser.add_argument("--base-url", help="API Gateway URL (used for both Identity and Directory calls)")
    parser.add_argument("--identity-url", help="Identity Service URL (overrides --base-url for login)")
    parser.add_argument("--directory-url", help="Directory Service URL (overrides --base-url for data)")
    parser.add_argument("--username", default="ADM001", help="Identity demo ADMIN account (default ADM001)")
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="Seconds per request; free-plan services can take ~1 minute to wake (default 90)")
    args = parser.parse_args(argv)

    identity_url = (args.identity_url or args.base_url or "").rstrip("/")
    directory_url = (args.directory_url or args.base_url or "").rstrip("/")
    if not identity_url or not directory_url:
        parser.error("give --base-url, or both --identity-url and --directory-url")

    password = os.environ.get("SEED_ADMIN_PASSWORD") or getpass.getpass(f"Password for {args.username}: ")

    try:
        with httpx.Client(base_url=identity_url, timeout=args.timeout) as identity, \
                httpx.Client(base_url=directory_url, timeout=args.timeout) as directory:
            print(f"Logging in as {args.username} at {identity_url}")
            headers = login(identity, args.username, password)
            print(f"Seeding synthetic demo data into {directory_url}")
            counts = seed(directory, headers)
    except (SeedError, httpx.HTTPError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Done: {counts['created']} created, {counts['skipped']} already existed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
