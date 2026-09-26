# University Directory Service: API Contract

**Status: draft, verified against implementation.** Not frozen: the contract may still change before other teams sign off. The examples were captured from the running application (commit series on `feature-pavithira/directory-service`); only the random ID suffixes were replaced with illustrative values.

All codes, names and identifiers in the examples (`FSYN`, `DEPT-SYN`, `SU-SYN`, `usr-syn-001`, …) are **synthetic**.

## 1. Conventions

| Item | Value |
|---|---|
| Base path | `/api/v1` (gateway base path: *to be confirmed*) |
| Liveness | `GET /health` (public, not versioned) |
| Format | JSON, UTF-8 |
| Auth header | `Authorization: Bearer <JWT issued by the Identity Service>` |
| Reads (`GET`) | any valid token |
| Writes (`POST`/`PUT`/`PATCH`/`DELETE`) | valid token with role `ADMIN` |
| Identifiers | 2–50 chars of `A–Z a–z 0–9 _ -` |
| Codes | 2–20 chars of `A–Z a–z 0–9 _ -`, stored upper-case |
| Entity references | Faculty, department and service-unit path/body references accept an **id or a code** (case-insensitive) unless stated otherwise. List filters take ids. |
| Pagination | `skip` (≥0, default 0), `limit` (1–500, default 100) |
| Timestamps | UTC, ISO-8601. With SQLite they are serialised without an offset. |

### 1.1 Response envelope

Success:

```json
{ "success": true, "data": { } }
```

Error:

```json
{ "success": false, "error": { "code": "FACULTY_NOT_FOUND", "message": "Faculty with identifier 'fac-x' was not found." } }
```

Request validation errors (422) add field details:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [ { "field": "body.code", "message": "Field required" } ]
  }
}
```

### 1.2 Errors that can occur on any endpoint

| Status | Code | When |
|---|---|---|
| 401 | `UNAUTHORIZED` | Token missing, malformed, bad signature, expired, wrong `iss`/`aud` (jwks mode), or the token subject is not an ACTIVE Identity user (identity-hs256 mode). Header `WWW-Authenticate: Bearer`. |
| 403 | `FORBIDDEN` | Write operation without role `ADMIN` |
| 422 | `VALIDATION_ERROR` | Body or query fails schema validation |
| 500 | `AUTH_NOT_CONFIGURED` | The service is missing the configuration for its `AUTH_MODE` |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error (no internals exposed) |
| 502 | `IDENTITY_SERVICE_ERROR` / `IDENTITY_SERVICE_BAD_RESPONSE` | Identity Service failed while authenticating (identity-hs256 mode) or checking a user |
| 503 | `IDENTITY_SERVICE_UNAVAILABLE` | Identity Service or its signing keys unreachable or timed out |

```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication credentials were not provided." } }
```
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication token has expired." } }
```
```json
{ "success": false, "error": { "code": "FORBIDDEN", "message": "This operation requires one of the roles: ADMIN." } }
```

### 1.3 Authentication modes

| | `identity-hs256` (current default) | `jwks` (target contract) |
|---|---|---|
| Algorithm | HS256, shared `JWT_SECRET_KEY` | RS256, public keys from `/.well-known/jwks.json` |
| Claims checked | `exp`, `sub` | `exp`, `sub`, `iss`, `aud` |
| Roles from | Identity validation endpoint (`data.roles`) | token `roles` claim |
| Identity call per request | yes | no |

The current Identity Service issues HS256 tokens without `roles`, `iss` or `aud`, and publishes no JWKS. It therefore **does not satisfy the `jwks` contract yet**; see the README section "Compatibility gap".

### 1.4 Deprecated unprefixed aliases

`/faculties`, `/departments`, `/service-units`, `/affiliations` and `/validation/...` still answer without the `/api/v1` prefix, with the same auth and behaviour. They are hidden from OpenAPI, and their responses add:

```
Deprecation: true
Link: </api/v1/faculties/fac-fsyn-3f9a1c>; rel="successor-version"
```

Consumers should migrate to `/api/v1`. The aliases will be removed after migration.

### 1.5 Identity Service dependency (outbound)

The Directory Service calls exactly one Identity endpoint:

```
GET {IDENTITY_SERVICE_BASE_URL}/validation/users/{user_id}?require_active=true
```

It uses only `data.user_id`, `data.status`, `data.is_valid` and `data.roles`. Failures map to `404 USER_NOT_FOUND`, `409 USER_INACTIVE`, `503 IDENTITY_SERVICE_UNAVAILABLE`, `502 IDENTITY_SERVICE_ERROR` or `502 IDENTITY_SERVICE_BAD_RESPONSE`, and downstream error text is never forwarded.

---

## 2. Validation endpoints (for dependent services)

All are `GET` with **any valid token** (no role required), and none call the Identity Service.

### 2.1 Validate faculty

`GET /api/v1/validation/faculties/{faculty_id}`: `faculty_id` is an id or code.

| Status | Code |
|---|---|
| 200 | `data.is_valid = true` |
| 400 | `INVALID_IDENTIFIER_FORMAT` |
| 404 | `FACULTY_NOT_FOUND` |

```json
{
  "success": true,
  "data": { "faculty_id": "fac-fsyn-3f9a1c", "code": "FSYN", "name": "Faculty of Synthetic Studies", "is_valid": true }
}
```
```json
{ "success": false, "error": { "code": "INVALID_IDENTIFIER_FORMAT", "message": "Faculty identifier 'bad$id' has an invalid format." } }
```

### 2.2 Validate department

`GET /api/v1/validation/departments/{department_id}`: id or code. Also confirms the parent faculty.

| Status | Code |
|---|---|
| 200 | `data.is_valid = true` |
| 400 | `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP` |
| 404 | `DEPARTMENT_NOT_FOUND` |

```json
{
  "success": true,
  "data": {
    "department_id": "dept-dept-syn-7b2e4d",
    "code": "DEPT-SYN",
    "name": "Department of Synthetic Data Science",
    "faculty_id": "fac-fsyn-3f9a1c",
    "faculty_name": "Faculty of Synthetic Studies",
    "is_valid": true
  }
}
```

### 2.3 Validate service unit

`GET /api/v1/validation/service-units/{unit_id}`: id or code.

| Status | Code |
|---|---|
| 200 | `data.is_valid = true` |
| 400 | `INVALID_IDENTIFIER_FORMAT` |
| 404 | `SERVICE_UNIT_NOT_FOUND` |

```json
{
  "success": true,
  "data": {
    "unit_id": "unit-su-syn-c81f05",
    "code": "SU-SYN",
    "name": "Synthetic Support Unit",
    "description": "Synthetic example unit",
    "is_valid": true
  }
}
```

### 2.4 Validate user affiliation

`GET /api/v1/validation/users/{user_id}/affiliation?department_id=&faculty_id=`

| Query | Required | Notes |
|---|---|---|
| `department_id` | no | id or code |
| `faculty_id` | no | id or code; if both are given, the department must belong to the faculty |

| Status | Code |
|---|---|
| 200 | `data.is_valid = true`, plus every matching affiliation |
| 400 | `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP` |
| 404 | `AFFILIATION_NOT_FOUND` (no match), `DEPARTMENT_NOT_FOUND`, `FACULTY_NOT_FOUND` (unknown filter) |

`GET /api/v1/validation/users/usr-syn-001/affiliation?department_id=DEPT-SYN`

```json
{
  "success": true,
  "data": {
    "user_id": "usr-syn-001",
    "is_valid": true,
    "affiliations": [
      {
        "affiliation_id": "aff-usr-syn-001-5d0a9e",
        "department": { "id": "dept-dept-syn-7b2e4d", "code": "DEPT-SYN", "name": "Department of Synthetic Data Science" },
        "faculty": { "id": "fac-fsyn-3f9a1c", "code": "FSYN", "name": "Faculty of Synthetic Studies" }
      }
    ]
  }
}
```
```json
{ "success": false, "error": { "code": "AFFILIATION_NOT_FOUND", "message": "No affiliation exists for user 'usr-syn-009' matching the requested criteria." } }
```

This endpoint checks Directory data only. Whether the user's account is active is the Identity Service's concern.

### 2.5 Validate user responsibilities

`GET /api/v1/validation/users/{user_id}/responsibilities?service_unit_id=&department_id=&faculty_id=`: all filters are optional **ids**.

| Status | Code |
|---|---|
| 200 | At least one matching ACTIVE responsibility; `data.is_valid = true` |
| 400 | `INVALID_IDENTIFIER_FORMAT` |
| 403 | `RESPONSIBILITY_INACTIVE` (matches exist but none is ACTIVE) |
| 404 | `RESPONSIBILITY_NOT_FOUND` |

```json
{
  "success": true,
  "data": {
    "user_id": "usr-syn-002",
    "is_valid": true,
    "responsibilities": [
      {
        "responsibility_id": "resp-9c4e1a7b2f30",
        "user_id": "usr-syn-002",
        "service_unit_id": "unit-su-syn-c81f05",
        "service_unit_name": "Synthetic Support Unit",
        "department_id": "dept-dept-syn-7b2e4d",
        "department_name": "Department of Synthetic Data Science",
        "faculty_id": null,
        "faculty_name": null,
        "role_title": "Unit Coordinator",
        "status": "ACTIVE"
      }
    ]
  }
}
```

---

## 3. Management endpoints

In the tables below, "Auth" is **Token** (any valid token) or **ADMIN** (valid token with role `ADMIN`).

### 3.1 Faculties

| Method | Path | Auth | Request | Success | Error codes |
|---|---|---|---|---|---|
| POST | `/api/v1/faculties` | ADMIN | `{code, name, description?}` | 201 | 400 `INVALID_IDENTIFIER_FORMAT`; 409 `FACULTY_CODE_ALREADY_EXISTS` |
| GET | `/api/v1/faculties?skip&limit` | Token | – | 200 list | – |
| GET | `/api/v1/faculties/{faculty_id}` | Token | id or code | 200 | 400 `INVALID_IDENTIFIER_FORMAT`; 404 `FACULTY_NOT_FOUND` |
| PUT | `/api/v1/faculties/{faculty_id}` | ADMIN | `{code?, name?, description?}` | 200 | 400; 404 `FACULTY_NOT_FOUND`; 409 `FACULTY_CODE_ALREADY_EXISTS` |
| DELETE | `/api/v1/faculties/{faculty_id}` | ADMIN | – | 200 | 400; 404 `FACULTY_NOT_FOUND`; 409 `FACULTY_HAS_DEPENDENCIES` |

A faculty with departments, affiliations or responsibilities cannot be deleted.

`POST /api/v1/faculties`

```json
{ "code": "FSYN", "name": "Faculty of Synthetic Studies", "description": "Synthetic example faculty" }
```
```json
{
  "success": true,
  "data": {
    "code": "FSYN",
    "name": "Faculty of Synthetic Studies",
    "description": "Synthetic example faculty",
    "id": "fac-fsyn-3f9a1c",
    "created_at": "2026-09-26T11:12:06.423885"
  }
}
```

`GET /api/v1/faculties` returns `{"success": true, "data": [ <faculty>, ... ]}`. `PUT` returns the updated faculty in the same shape as `POST`.

`DELETE /api/v1/faculties/fac-fsyn-3f9a1c` (still has dependents):

```json
{
  "success": false,
  "error": {
    "code": "FACULTY_HAS_DEPENDENCIES",
    "message": "Faculty 'FSYN' cannot be deleted while dependent records exist: 1 department(s), 1 affiliation(s). Remove or reassign them first."
  }
}
```

A successful delete returns:

```json
{ "success": true, "data": { "message": "Faculty 'fac-fsyn-3f9a1c' was successfully deleted." } }
```

### 3.2 Departments

| Method | Path | Auth | Request | Success | Error codes |
|---|---|---|---|---|---|
| POST | `/api/v1/departments` | ADMIN | `{code, name, faculty_id}` (faculty id or code) | 201 | 400 `INVALID_IDENTIFIER_FORMAT`; 404 `FACULTY_NOT_FOUND`; 409 `DEPARTMENT_CODE_ALREADY_EXISTS` |
| GET | `/api/v1/departments?skip&limit&faculty_id` | Token | – | 200 list | – |
| GET | `/api/v1/departments/{department_id}` | Token | id or code | 200 | 400; 404 `DEPARTMENT_NOT_FOUND` |
| PUT / PATCH | `/api/v1/departments/{department_id}` | ADMIN | `{code?, name?, faculty_id?}` (partial) | 200 | 400; 404 `DEPARTMENT_NOT_FOUND` / `FACULTY_NOT_FOUND`; 409 `DEPARTMENT_CODE_ALREADY_EXISTS` |
| DELETE | `/api/v1/departments/{department_id}` | ADMIN | – | 200 | 400; 404; 409 `DEPARTMENT_HAS_DEPENDENCIES` |

A department with affiliations or responsibilities cannot be deleted.

`POST /api/v1/departments`

```json
{ "code": "DEPT-SYN", "name": "Department of Synthetic Data", "faculty_id": "FSYN" }
```
```json
{
  "success": true,
  "data": {
    "code": "DEPT-SYN",
    "name": "Department of Synthetic Data",
    "faculty_id": "fac-fsyn-3f9a1c",
    "id": "dept-dept-syn-7b2e4d",
    "created_at": "2026-09-26T11:12:06.491486",
    "updated_at": "2026-09-26T11:12:06.491486"
  }
}
```
```json
{
  "success": false,
  "error": {
    "code": "DEPARTMENT_HAS_DEPENDENCIES",
    "message": "Department 'DEPT-SYN' cannot be deleted while dependent records exist: 1 affiliation(s), 1 responsibility(ies). Remove or reassign them first."
  }
}
```

### 3.3 Service units

Service units are standalone: they do not belong to a faculty or department.

| Method | Path | Auth | Request | Success | Error codes |
|---|---|---|---|---|---|
| POST | `/api/v1/service-units` | ADMIN | `{code, name, description?}` | 201 | 400 `INVALID_IDENTIFIER_FORMAT`; 409 `SERVICE_UNIT_CODE_ALREADY_EXISTS` |
| GET | `/api/v1/service-units?skip&limit` | Token | – | 200 list | – |
| GET | `/api/v1/service-units/{service_unit_id}` | Token | id or code | 200 | 400; 404 `SERVICE_UNIT_NOT_FOUND` |
| PUT | `/api/v1/service-units/{service_unit_id}` | ADMIN | `{code?, name?, description?}` | 200 | 400; 404; 409 `SERVICE_UNIT_CODE_ALREADY_EXISTS` |
| DELETE | `/api/v1/service-units/{service_unit_id}` | ADMIN | – | 200 | 400; 404; 409 `SERVICE_UNIT_HAS_DEPENDENCIES` |

```json
{ "code": "SU-SYN", "name": "Synthetic Support Unit", "description": "Synthetic example unit" }
```
```json
{
  "success": true,
  "data": {
    "code": "SU-SYN",
    "name": "Synthetic Support Unit",
    "description": "Synthetic example unit",
    "id": "unit-su-syn-c81f05",
    "created_at": "2026-09-26T11:12:06.519325"
  }
}
```
```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNIT_HAS_DEPENDENCIES",
    "message": "Service unit 'SU-SYN' cannot be deleted while dependent records exist: 1 responsibility(ies). Remove or reassign them first."
  }
}
```

### 3.4 User affiliations

An affiliation links an Identity user to a department (and its faculty). A user may have one affiliation per department.

| Method | Path | Auth | Request | Success | Error codes |
|---|---|---|---|---|---|
| POST | `/api/v1/affiliations` | ADMIN | `{user_id, department_id, faculty_id?}` | 201 | 400 `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP`; 404 `DEPARTMENT_NOT_FOUND`, `FACULTY_NOT_FOUND`, `USER_NOT_FOUND`; 409 `AFFILIATION_ALREADY_EXISTS`, `USER_INACTIVE`; 502/503 Identity errors |
| GET | `/api/v1/affiliations?skip&limit&department_id&faculty_id&user_id` | Token | filters are ids | 200 list | – |
| GET | `/api/v1/affiliations/{affiliation_id}` | Token | – | 200 | 400; 404 `AFFILIATION_NOT_FOUND` |
| GET | `/api/v1/affiliations/users/{user_id}` | Token | – | 200 (first affiliation of the user) | 400; 404 `AFFILIATION_NOT_FOUND` |
| PUT | `/api/v1/affiliations/{affiliation_id}` | ADMIN | `{department_id?, faculty_id?}` | 200 | as POST, plus 404 `AFFILIATION_NOT_FOUND` |
| DELETE | `/api/v1/affiliations/{affiliation_id}` | ADMIN | – | 200 | 400; 404 `AFFILIATION_NOT_FOUND` |

Create and update first check the user with the Identity Service. The user must exist and be ACTIVE; on update, the already-stored user is re-checked. If `faculty_id` is omitted, the department's faculty is used.

`POST /api/v1/affiliations`

```json
{ "user_id": "usr-syn-001", "department_id": "DEPT-SYN" }
```
```json
{
  "success": true,
  "data": {
    "id": "aff-usr-syn-001-5d0a9e",
    "user_id": "usr-syn-001",
    "department_id": "dept-dept-syn-7b2e4d",
    "department_name": "Department of Synthetic Data Science",
    "department_code": "DEPT-SYN",
    "faculty_id": "fac-fsyn-3f9a1c",
    "faculty_name": "Faculty of Synthetic Studies",
    "faculty_code": "FSYN",
    "created_at": "2026-09-26T11:12:06.541405",
    "updated_at": "2026-09-26T11:12:06.541405"
  }
}
```

Identity-related errors:

```json
{ "success": false, "error": { "code": "USER_NOT_FOUND", "message": "User 'usr-syn-unknown' was not found in the Identity Service." } }
```
```json
{ "success": false, "error": { "code": "USER_INACTIVE", "message": "User 'usr-syn-inactive' is not active in the Identity Service." } }
```
```json
{ "success": false, "error": { "code": "IDENTITY_SERVICE_UNAVAILABLE", "message": "The Identity Service is currently unavailable. Please retry later." } }
```
```json
{ "success": false, "error": { "code": "AFFILIATION_ALREADY_EXISTS", "message": "User 'usr-syn-001' is already affiliated with Department 'Department of Synthetic Data Science'." } }
```

### 3.5 Service responsibilities

A responsibility assigns a role title to an Identity user for **at least one** of a service unit, department or faculty.

| Method | Path | Auth | Request | Success | Error codes |
|---|---|---|---|---|---|
| POST | `/api/v1/responsibilities` | ADMIN | `{user_id, service_unit_id?, department_id?, faculty_id?, role_title, status?}` | 201 | 400 `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP`; 404 `SERVICE_UNIT_NOT_FOUND`, `DEPARTMENT_NOT_FOUND`, `FACULTY_NOT_FOUND`, `USER_NOT_FOUND`; 409 `RESPONSIBILITY_ALREADY_EXISTS`, `USER_INACTIVE`; 422 `VALIDATION_ERROR` (no target); 502/503 Identity errors |
| GET | `/api/v1/responsibilities?skip&limit&user_id&service_unit_id&department_id&faculty_id&status` | Token | filters are ids; `status` = `ACTIVE`/`INACTIVE` | 200 list | 422 (bad status) |
| GET | `/api/v1/responsibilities/{responsibility_id}` | Token | – | 200 | 400; 404 `RESPONSIBILITY_NOT_FOUND` |
| PUT | `/api/v1/responsibilities/{responsibility_id}` | ADMIN | `{service_unit_id?, department_id?, faculty_id?, role_title?, status?}` | 200 | as POST, plus 404 `RESPONSIBILITY_NOT_FOUND` |
| DELETE | `/api/v1/responsibilities/{responsibility_id}` | ADMIN | – | 200 | 400; 404 `RESPONSIBILITY_NOT_FOUND` |

Rules:

- `status` defaults to `ACTIVE`.
- Unit, department and faculty references accept an id or a code and are stored as ids. A department given together with a faculty must belong to it.
- When the resulting responsibility is **ACTIVE**, two checks apply:
  - The user must exist and be ACTIVE in the Identity Service.
  - No other ACTIVE responsibility may exist for the same user and the same `(service_unit_id, department_id, faculty_id)`; otherwise `409 RESPONSIBILITY_ALREADY_EXISTS`.
- Setting `status` to `INACTIVE`, or deleting, does not call the Identity Service. This lets admins close records of users who have left.

`POST /api/v1/responsibilities`

```json
{ "user_id": "usr-syn-002", "service_unit_id": "SU-SYN", "department_id": "DEPT-SYN", "role_title": "Unit Coordinator" }
```
```json
{
  "success": true,
  "data": {
    "id": "resp-9c4e1a7b2f30",
    "user_id": "usr-syn-002",
    "service_unit_id": "unit-su-syn-c81f05",
    "service_unit_code": "SU-SYN",
    "service_unit_name": "Synthetic Support Unit",
    "department_id": "dept-dept-syn-7b2e4d",
    "department_code": "DEPT-SYN",
    "department_name": "Department of Synthetic Data Science",
    "faculty_id": null,
    "faculty_code": null,
    "faculty_name": null,
    "role_title": "Unit Coordinator",
    "status": "ACTIVE",
    "created_at": "2026-09-26T11:12:06.616809",
    "updated_at": "2026-09-26T11:12:06.616809"
  }
}
```

`PUT /api/v1/responsibilities/resp-9c4e1a7b2f30` with `{"status": "INACTIVE"}` returns the same shape with `"status": "INACTIVE"`.

```json
{ "success": false, "error": { "code": "RESPONSIBILITY_ALREADY_EXISTS", "message": "User 'usr-syn-002' already has an active responsibility for this organizational unit." } }
```
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [ { "field": "body", "message": "Value error, At least one of service_unit_id, department_id or faculty_id is required." } ]
  }
}
```

---

## 4. Error code index

| Code | Status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body/query failed schema validation |
| `INVALID_IDENTIFIER_FORMAT` | 400 | Identifier or code has an invalid format |
| `INVALID_ORGANIZATIONAL_RELATIONSHIP` | 400 | Department does not belong to the given faculty (or has no valid faculty) |
| `UNAUTHORIZED` | 401 | Missing/invalid/expired token or inactive token subject |
| `FORBIDDEN` | 403 | Role `ADMIN` required |
| `RESPONSIBILITY_INACTIVE` | 403 | Validation: matching responsibilities exist but none is ACTIVE |
| `NOT_FOUND` | 404 | Unknown route |
| `FACULTY_NOT_FOUND` / `DEPARTMENT_NOT_FOUND` / `SERVICE_UNIT_NOT_FOUND` | 404 | Referenced directory entity does not exist |
| `AFFILIATION_NOT_FOUND` | 404 | No matching affiliation |
| `RESPONSIBILITY_NOT_FOUND` | 404 | No matching responsibility |
| `USER_NOT_FOUND` | 404 | Identity Service does not know the user |
| `FACULTY_CODE_ALREADY_EXISTS` / `DEPARTMENT_CODE_ALREADY_EXISTS` / `SERVICE_UNIT_CODE_ALREADY_EXISTS` | 409 | Duplicate code |
| `AFFILIATION_ALREADY_EXISTS` | 409 | User already affiliated with the department |
| `RESPONSIBILITY_ALREADY_EXISTS` | 409 | Duplicate ACTIVE responsibility for the same user and scope |
| `FACULTY_HAS_DEPENDENCIES` / `DEPARTMENT_HAS_DEPENDENCIES` / `SERVICE_UNIT_HAS_DEPENDENCIES` | 409 | Delete refused because dependent records exist |
| `USER_INACTIVE` | 409 | User is not ACTIVE in the Identity Service |
| `AUTH_NOT_CONFIGURED` | 500 | Service misconfiguration for the selected `AUTH_MODE` |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected error |
| `IDENTITY_SERVICE_ERROR` | 502 | Identity Service returned an error status |
| `IDENTITY_SERVICE_BAD_RESPONSE` | 502 | Identity Service response was malformed |
| `IDENTITY_SERVICE_UNAVAILABLE` | 503 | Identity Service or its signing keys unreachable or timed out |

## 5. Open items (to agree with other teams)

1. Gateway base path in front of `/api/v1`.
2. The Identity Service changes needed for `AUTH_MODE=jwks` (RS256, JWKS endpoint, `iss`/`aud`/`roles` claims, token issuing), listed in the README.
3. Date for removing the unprefixed deprecated aliases.
4. Whether the validation endpoints should stay token-protected or accept a service-to-service credential.
5. Whether the stored `user_id` should be normalised to the Identity Service's canonical id (today it is stored as sent).
