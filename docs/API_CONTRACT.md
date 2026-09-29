# University Directory Service: API Contract

**Owner:** Group 5 (Identity & University Directory) · **Contract version:** v1 (`/api/v1`) · **Status: draft, verified against implementation.** Not frozen: the contract may still change before other teams sign off.

**Audience:** Groups 6, 7 and 8, the Identity Service (also Group 5), the shared frontend team and the API Gateway team.

The examples were captured from the running application; only the random ID suffixes were replaced with illustrative values. All codes, names and identifiers in the examples (`FSYN`, `DEPT-SYN`, `SU-SYN`, `usr-syn-001`, …) are **synthetic**. Machine-readable versions: [openapi.json](openapi.json) and the Postman collection in [postman/](postman/). For a per-team summary of which endpoints to call, see [API_GUIDE_FOR_TEAMS.md](API_GUIDE_FOR_TEAMS.md).

## 1. Conventions

| Item | Value |
|---|---|
| Base path | `/api/v1` (gateway base path: *to be confirmed*) |
| Liveness | `GET /health` (public, not versioned) |
| Swagger / OpenAPI | `{base}/docs` · `{base}/openapi.json` |
| Format | JSON, UTF-8 |
| Auth header | `Authorization: Bearer <access token from the Identity Service>` (Identity API contract v1: RS256, `iss` `university-identity-service`, `aud` `university-services-platform`) |
| Reads (`GET`) | any valid token |
| Writes (`POST`/`PUT`/`PATCH`/`DELETE`) | valid token with role `ADMIN`, confirmed live with the Identity Service |
| Identifiers | 2–50 chars of `A–Z a–z 0–9 _ -` |
| User ids | Writes accept an Identity user id or university id; the canonical Identity user id (JWT `sub`) is stored and returned. Reads and validation endpoints take the canonical id. |
| Codes | 2–20 chars of `A–Z a–z 0–9 _ -`, stored upper-case |
| Entity references | Faculty, department and service-unit path/body references accept an **id or a code** (case-insensitive) unless stated otherwise. List filters and the responsibility-validation filters take ids. |
| Pagination | `skip` (≥0, default 0), `limit` (1–500, default 100) |
| Search | List endpoints accept `q` (case-insensitive substring, max 100 chars; `%` and `_` are literal) |
| Timestamps | UTC, ISO-8601. With SQLite they are serialised without an offset. |

`GET /health` needs no token and does not use the response envelope:

```json
{ "status": "healthy", "service": "directory-service", "version": "1.0.0" }
```

### 1.1 Response envelope

Success:

```json
{ "success": true, "data": { } }
```

Error:

```json
{ "success": false, "error": { "code": "FACULTY_NOT_FOUND", "message": "Faculty with identifier 'fac-x' was not found." } }
```

Branch on `error.code`, which is stable; `error.message` is for people and may change. Request validation errors (422) add field details:

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
| 401 | `UNAUTHORIZED` | Token missing, malformed, bad signature, expired, wrong `iss`/`aud`; or, on a write, the Identity Service no longer knows the caller or rejects the token. Header `WWW-Authenticate: Bearer`. |
| 403 | `FORBIDDEN` | Write without role `ADMIN`, including when the role was revoked or the account deactivated after the token was issued |
| 404 | `NOT_FOUND` | Unknown route |
| 405 | `METHOD_NOT_ALLOWED` | Route exists but not for this HTTP method |
| 422 | `VALIDATION_ERROR` | Body or query fails schema validation |
| 500 | `AUTH_NOT_CONFIGURED` | The service is missing the configuration for its `AUTH_MODE` |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected error (no internals exposed) |
| 502 | `IDENTITY_SERVICE_ERROR` / `IDENTITY_SERVICE_BAD_RESPONSE` | The Identity Service answered outside its contract during a write |
| 503 | `IDENTITY_SERVICE_UNAVAILABLE` | Identity Service or its signing keys unreachable or timed out. **Retry later; nothing was written.** |

```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication credentials were not provided." } }
```
```json
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "Authentication token has expired." } }
```
```json
{ "success": false, "error": { "code": "FORBIDDEN", "message": "This operation requires one of the roles: ADMIN." } }
```

### 1.3 Authentication

The Directory Service verifies tokens issued under the **Identity API contract v1** (`AUTH_MODE=jwks`, the default):

- RS256 signature checked against `GET {identity}/.well-known/jwks.json`, using the key whose `kid` matches the token header. The key set is cached and re-fetched for an unknown `kid`.
- `iss == university-identity-service`, `aud == university-services-platform`, `exp` not passed, `sub` present.
- Roles come from the `roles` claim. They are a **login-time snapshot**, so:
  - **Reads** trust the token and make no Identity call.
  - **Writes** re-confirm the caller live: `GET {identity}/api/v1/validation/users/{sub}?required_role=ADMIN`. A revoked role or an inactive account gives `403 FORBIDDEN`; a deleted user gives `401 UNAUTHORIZED`; an Identity outage gives `503`.

A legacy `AUTH_MODE=identity-hs256` exists only for the Sprint 1 Identity Service (HS256 with a shared secret) and is not used with the v1 Identity Service.

### 1.4 Deprecated unprefixed aliases

`/faculties`, `/departments`, `/service-units`, `/affiliations` and `/validation/...` still answer without the `/api/v1` prefix, with the same auth and behaviour. They are hidden from OpenAPI, and their **successful** responses add the headers below. Error responses from an alias (for example a 401) do not carry them.

```
Deprecation: true
Link: </api/v1/faculties/fac-fsyn-3f9a1c>; rel="successor-version"
```

Consumers should migrate to `/api/v1`. The aliases will be removed after migration.

### 1.5 Identity Service dependency (outbound)

The Directory Service calls the Identity Service's user validation endpoint, forwarding the **caller's own** `Authorization` header (as Identity contract §3.4 requires):

```
GET {IDENTITY_SERVICE_BASE_URL}/api/v1/validation/users/{user_id}[?required_role=ADMIN]
```

It is called:

- on every write, to confirm the caller still holds `ADMIN` (section 1.3)
- on affiliation create/update, to check that the affiliated user exists and is ACTIVE
- on responsibility create (the user must exist, and be ACTIVE if the responsibility is ACTIVE), and on responsibility update when the result is ACTIVE

`require_active` is not sent. An inactive target user is read from the body (`is_valid: false`), so an Identity `403 ACCOUNT_INACTIVE` can only mean the caller's account is inactive.

Only `data.user_id`, `data.status`, `data.is_valid`, `data.roles` and `data.is_authorized` are used. Downstream error text is never forwarded. Failures map to:

| Identity outcome | Directory response |
|---|---|
| Unknown user (`404`) | `404 USER_NOT_FOUND` |
| Target user inactive (`200`, `is_valid: false`) where an active user is required | `409 USER_INACTIVE` |
| Caller token rejected (`401`) | `401 UNAUTHORIZED` |
| Caller account inactive (`403 ACCOUNT_INACTIVE`) | `403 FORBIDDEN` |
| Timeout / connection error | `503 IDENTITY_SERVICE_UNAVAILABLE` |
| `5xx`, other status, malformed body | `502 IDENTITY_SERVICE_ERROR` / `502 IDENTITY_SERVICE_BAD_RESPONSE` |

In both cases nothing is written.

---

## 2. Validation endpoints (for dependent services)

All are `GET` with **any valid token** (no role required; forward your user's token). They answer from Directory data only and make no Identity call. For decisions that combine a user's **role** with a relationship, use the Identity Service's eligibility endpoint (Identity contract §6.3), which calls these Directory APIs for you.

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
| GET | `/api/v1/faculties?skip&limit&q` | Token | `q` searches code, name, description | 200 list (ordered by code) | 422 |
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
| GET | `/api/v1/departments?skip&limit&faculty_id&q` | Token | `q` searches code, name | 200 list (ordered by code) | 422 |
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
| GET | `/api/v1/service-units?skip&limit&q` | Token | `q` searches code, name, description | 200 list (ordered by code) | 422 |
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
| GET | `/api/v1/affiliations?skip&limit&department_id&faculty_id&user_id&q` | Token | filters are ids; `q` searches user id and department/faculty code and name | 200 list | 422 |
| GET | `/api/v1/affiliations/{affiliation_id}` | Token | – | 200 | 400; 404 `AFFILIATION_NOT_FOUND` |
| GET | `/api/v1/affiliations/users/{user_id}` | Token | – | 200 (first affiliation of the user) | 400; 404 `AFFILIATION_NOT_FOUND` |
| PUT | `/api/v1/affiliations/{affiliation_id}` | ADMIN | `{department_id?, faculty_id?}` | 200 | 400 `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP`; 404 `AFFILIATION_NOT_FOUND`, `DEPARTMENT_NOT_FOUND`, `FACULTY_NOT_FOUND`, `USER_NOT_FOUND`; 409 `AFFILIATION_ALREADY_EXISTS`, `USER_INACTIVE`; 502/503 Identity errors |
| DELETE | `/api/v1/affiliations/{affiliation_id}` | ADMIN | – | 200 | 400; 404 `AFFILIATION_NOT_FOUND` |

`user_id` may be an Identity user id or a university id (e.g. `STU001`); the canonical Identity user id (e.g. `usr-student-001`) is stored and returned. The user must exist and be ACTIVE in the Identity Service:

- On create, this is checked right after the `user_id` format check and before any directory lookup.
- On update, the stored user is re-checked after the affiliation is loaded. `user_id` itself cannot be changed.

If `faculty_id` is omitted, the department's faculty is used.

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
| GET | `/api/v1/responsibilities?skip&limit&user_id&service_unit_id&department_id&faculty_id&status&q` | Token | filters are ids; `status` = `ACTIVE`/`INACTIVE`; `q` searches user id, role title and unit/department/faculty code and name | 200 list | 422 |
| GET | `/api/v1/responsibilities/{responsibility_id}` | Token | – | 200 | 400; 404 `RESPONSIBILITY_NOT_FOUND` |
| PUT | `/api/v1/responsibilities/{responsibility_id}` | ADMIN | `{service_unit_id?, department_id?, faculty_id?, role_title?, status?}` | 200 | 400 `INVALID_IDENTIFIER_FORMAT`, `INVALID_ORGANIZATIONAL_RELATIONSHIP`; 404 `RESPONSIBILITY_NOT_FOUND`, `SERVICE_UNIT_NOT_FOUND`, `DEPARTMENT_NOT_FOUND`, `FACULTY_NOT_FOUND`, `USER_NOT_FOUND`; 409 `RESPONSIBILITY_ALREADY_EXISTS`, `USER_INACTIVE`; 422 `VALIDATION_ERROR`; 502/503 Identity errors (user checks only when the result is ACTIVE). `user_id` cannot be changed and references cannot be cleared. |
| DELETE | `/api/v1/responsibilities/{responsibility_id}` | ADMIN | – | 200 | 400; 404 `RESPONSIBILITY_NOT_FOUND` |

Rules:

- `status` defaults to `ACTIVE`.
- Unit, department and faculty references accept an id or a code and are stored as ids. A department given together with a faculty must belong to it.
- `user_id` may be an Identity user id or a university id; the canonical Identity user id is stored. On create the user must always exist in the Identity Service (`404 USER_NOT_FOUND`).
- When the resulting responsibility is **ACTIVE**, two checks apply:
  - The user must be ACTIVE in the Identity Service (`409 USER_INACTIVE`).
  - No other ACTIVE responsibility may exist for the same user and the same `(service_unit_id, department_id, faculty_id)`; otherwise `409 RESPONSIBILITY_ALREADY_EXISTS`.
- Setting `status` to `INACTIVE`, or deleting, makes no user check (only the caller's ADMIN role is confirmed). This lets admins close records of users who have left, and create INACTIVE historical records for inactive users.

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
| `UNAUTHORIZED` | 401 | Missing/invalid/expired token, or the Identity Service no longer accepts the caller |
| `FORBIDDEN` | 403 | Role `ADMIN` required (checked in the token and confirmed live on writes), or the caller's account is inactive |
| `RESPONSIBILITY_INACTIVE` | 403 | Validation: matching responsibilities exist but none is ACTIVE |
| `NOT_FOUND` | 404 | Unknown route |
| `METHOD_NOT_ALLOWED` | 405 | Route exists but not for this HTTP method |
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
| `IDENTITY_SERVICE_ERROR` | 502 | Identity Service returned an unexpected error status |
| `IDENTITY_SERVICE_BAD_RESPONSE` | 502 | Identity Service response was malformed |
| `IDENTITY_SERVICE_UNAVAILABLE` | 503 | Identity Service or its signing keys unreachable or timed out |

## 5. Notes for the Identity Service (Group 5)

The Identity contract (§7) lists Directory endpoints for its eligibility checks. To work with the Directory Service:

1. **Forward the user's token.** Every Directory endpoint except `/health` needs `Authorization: Bearer <token>`. The Identity eligibility endpoint should forward the token it received, exactly as Identity §3.4 asks of other services.
2. **Use `/api/v1` paths.** The unprefixed paths in Identity §7 (`/validation/...`, `/affiliations/...`, `/faculties`, …) still work but are deprecated.
3. **For `relationship=AFFILIATION`**, prefer `GET /api/v1/validation/users/{user_id}/affiliation?department_id=&faculty_id=` (section 2.4). It returns **every** matching affiliation. `GET /api/v1/affiliations/users/{user_id}` returns only the user's first affiliation, which gives wrong answers for users in more than one department.
4. **For `relationship=RESPONSIBILITY`**, use `GET /api/v1/validation/users/{user_id}/responsibilities?service_unit_id=&department_id=&faculty_id=` (section 2.5). The filters take ids, not codes.
5. **Pass the canonical user id** (JWT `sub`, e.g. `usr-student-001`), not the university id. That is what the Directory Service stores.
6. **Error mapping.** A Directory `503 IDENTITY_SERVICE_UNAVAILABLE` or 5xx should become Identity's `DEPENDENCY_UNAVAILABLE`, and never "eligible". A `404 AFFILIATION_NOT_FOUND` / `RESPONSIBILITY_NOT_FOUND` means "no relationship". `403 RESPONSIBILITY_INACTIVE` means the relationship exists but is inactive.

## 6. Open items (to agree with other teams)

1. Gateway base path in front of `/api/v1` (suggested, mirroring Identity: `/directory/**` → strip prefix; *to be confirmed* by the Gateway team).
2. Date for removing the unprefixed deprecated aliases.
3. Whether the Identity eligibility endpoint adopts the notes in section 5.

## 7. Change log

| Version | Change |
|---|---|
| v1 (draft) | Versioned API under `/api/v1`; JWT auth; ADMIN writes; 409 delete protection; service responsibility CRUD; affiliation validation endpoint; `q` search on lists. |
| v1 (draft, update) | Aligned with Identity API contract v1: `jwks` is the default auth mode (RS256, JWKS, `iss`/`aud`/`roles`); writes confirm ADMIN live; Identity calls use `/api/v1/validation/users/{id}` with the caller's token forwarded; canonical Identity user ids are stored; responsibility `user_id` widened to 50 characters. |
