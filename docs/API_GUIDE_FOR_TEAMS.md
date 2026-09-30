# Group 5 APIs: Which Endpoint Each Team Should Use

**From:** Group 5 (Identity & University Directory) · **For:** Groups 6, 7 and 8, the shared frontend team and the API Gateway team · **Status:** draft, verified against the running services (2026-09-30)

This page tells each team which Group 5 endpoints to call and when. Full request/response details:

- Directory Service: [API_CONTRACT.md](API_CONTRACT.md), [openapi.json](openapi.json), Postman collection in [postman/](postman/)
- Identity Service: `docs/API_CONTRACT.md` in the [University-identity-service](https://github.com/University-Service-Platform/University-identity-service) repo

All examples use synthetic data.

## 1. Two services, two jobs

| Service | Owns | Base URL (local) | Hosted |
|---|---|---|---|
| **Identity Service** | users, login, JWTs, roles, account status, eligibility decisions | `http://localhost:8001` | `https://university-identity-service.onrender.com` |
| **Directory Service** | faculties, departments, service units, who is affiliated with a department, who is responsible for a unit | `http://localhost:8002` | `https://university-directory-service.onrender.com` |

Both use the prefix `/api/v1`, the same envelope `{"success": true, "data": ...}` / `{"success": false, "error": {"code", "message"}}`, and the same JWT. Through the **API Gateway** (`https://university-api-gateway.onrender.com`) both services are reached with the same `/api/v1/...` paths. Read the base URLs from configuration (e.g. `IDENTITY_SERVICE_BASE_URL`, `DIRECTORY_SERVICE_BASE_URL`), and don't hard-code them.

## 2. Which question goes where

| Your question | Call |
|---|---|
| Who is logged in? | Identity `GET /api/v1/auth/me` |
| Does user X exist and is the account active? | Identity `GET /api/v1/validation/users/{user_id}` |
| Does user X hold role R? | Identity `GET /api/v1/validation/users/{user_id}?required_role=R` |
| **May user X do this?** (role + department/service responsibility; the platform's key business rule) | Identity `GET /api/v1/validation/users/{user_id}/eligibility?required_role=R&relationship=...` |
| Does faculty / department / service unit Z exist? What's its name? | Directory `GET /api/v1/validation/faculties/{id or code}`, `/validation/departments/{id or code}`, `/validation/service-units/{id or code}` |
| Lists for dropdowns and search | Directory `GET /api/v1/faculties`, `/departments?faculty_id=`, `/service-units`, all with `?q=` search |
| Is user X affiliated with department D / faculty F? | Directory `GET /api/v1/validation/users/{user_id}/affiliation?department_id=&faculty_id=` |
| Is user X responsible for service unit S? | Directory `GET /api/v1/validation/users/{user_id}/responsibilities?service_unit_id=` |
| Everyone in department D or faculty F (e.g. announcement audiences) | Directory `GET /api/v1/affiliations?department_id=` or `?faculty_id=` (paged) |
| Everyone responsible for service unit S | Directory `GET /api/v1/responsibilities?service_unit_id=&status=ACTIVE` |

**Rule of thumb:** for yes/no authorization decisions about a *person*, prefer the Identity **eligibility** endpoint, which checks account, role and relationship in one call. Use the Directory endpoints for organisational data and lists.

## 3. Rules for every team

1. **Get tokens from the Identity Service.** Call `POST /api/v1/auth/login`, then send `Authorization: Bearer <token>` on every call to Group 5.
2. **Forward the user's token when your service calls Group 5 on the user's behalf.** Every endpoint except `/health` needs one. Any active user's token is accepted for validation calls.
3. **Verify JWTs with JWKS.** Use `GET {identity}/.well-known/jwks.json`, RS256, `iss = university-identity-service`, `aud = university-services-platform`.
   - Tokens carry **`roles` (a list)**, `sub`, `university_id` and `account_type`.
   - Tokens carry **no department or service-unit claim.** Look those up through the Directory Service.
   - `roles` is a login-time snapshot: re-check with Identity before protected actions.
4. **Store references as IDs.**
   - Store users by `sub` / `user_id` (e.g. `usr-student-001`), not by name, email or university ID.
   - Store departments and service units by their Directory `id` (e.g. `dept-cs-cea025`) or stable **code** (e.g. `CS`), never by free-text name.
   - The random ID suffix differs per environment, so look IDs up and don't hard-code them.
5. **Branch on `error.code`, not on the message.**
   - `503 IDENTITY_SERVICE_UNAVAILABLE` from the Directory, or `503 DEPENDENCY_UNAVAILABLE` from Identity, means "unknown, try again". **Never treat it as allowed.**
6. **Only ADMIN can change directory data** (create/update/delete). Everyone with a valid token can read it.

---

## 4. Group 6: Facilities and Reservations

*Assignment: "Consumes user, role, and department validation from Group 5."*

| When | Call | Use the result |
|---|---|---|
| Verifying incoming JWTs (both services) | `GET {identity}/.well-known/jwks.json` | Your `JWT_JWK_SET_URI` already supports this: point it at the Identity JWKS URL |
| Resource manager creates or edits a resource owned by a department | Directory `GET /api/v1/validation/departments/{id or code}` | `200` + `data.is_valid` → store `data.department_id`; `404 DEPARTMENT_NOT_FOUND` → reject |
| Department picker in the resource form | Directory `GET /api/v1/departments?q=` | `data[]` with `id`, `code`, `name`, `faculty_id` |
| User requests a department-restricted resource | Identity `GET /api/v1/validation/users/{user_id}/eligibility?relationship=AFFILIATION&department_id={dept}` | Book only if `data.eligible`; otherwise show `data.message` |
| User requests a role-restricted resource | same, with `required_role=ACADEMIC_STAFF` (etc.) | same |
| Approver approves or rejects a reservation for a department's resource | Identity `.../eligibility?required_role=RESOURCE_MANAGER&relationship=RESPONSIBILITY&department_id={dept id}` (for `RESPONSIBILITY`, pass the Directory **id**; codes are only accepted for `AFFILIATION`) | Approve only if `data.eligible`; on `503` do **not** approve |

**About your `UserValidationData` record `{userId, active, roles, department, serviceUnit, message}`.** No single Group 5 endpoint returns that shape. Fill it like this:

- `userId`, `active`, `roles` come from Identity `GET /api/v1/validation/users/{user_id}`: `data.user_id`, `data.is_valid`, `data.roles`.
- `department` comes from Directory `GET /api/v1/validation/users/{user_id}/affiliation`: `data.affiliations[].department`.
- `serviceUnit` comes from Directory `GET /api/v1/validation/users/{user_id}/responsibilities`: `data.responsibilities[].service_unit_id` / `service_unit_name`.
- `message` comes from the eligibility endpoint's `data.message` (made for display).

For yes/no decisions, the single eligibility call is simpler than assembling this record.

Example: may this user book a resource restricted to the synthetic department `DEPT-SYN`?

```
GET {identity}/api/v1/validation/users/usr-student-001/eligibility?relationship=AFFILIATION&department_id=DEPT-SYN
Authorization: Bearer <user's token>
```
```json
{ "success": true, "data": { "user_id": "usr-student-001", "eligible": true, "reasons": [], "message": "User is eligible.", "…": "…" } }
```

## 5. Group 7: Service Requests and Work Orders

*Assignment: "Consumes user, role, department, and service-unit validation from Group 5."*

| When | Call | Use the result |
|---|---|---|
| Replacing the Sprint 1 placeholder JWT | Identity login + JWKS verification (section 3) | Read **`roles[]`**, not `role`. There is **no `department` claim**; see the next rows |
| Service desk triages or escalates a request and sets `responsibleServiceUnit` | Directory `GET /api/v1/validation/service-units/{id or code}` | `200` → store `data.unit_id` (or the code) instead of free text such as "Facilities"; `404 SERVICE_UNIT_NOT_FOUND` → reject |
| Unit picker for triage and escalation | Directory `GET /api/v1/service-units?q=` | `data[]` with `id`, `code`, `name` |
| Protected status change (only the authorized service desk may triage/assign/close) | Identity `.../eligibility?required_role=SERVICE_DESK_OFFICER&relationship=RESPONSIBILITY&service_unit_id={unit}` | Allow only if `data.eligible` |
| Technician updates an assigned work order | Identity `GET /api/v1/validation/users/{user_id}?required_role=TECHNICIAN` | Allow only if `data.is_valid` **and** `data.is_authorized`; also check the technician is the assignee in your own data |
| Showing "responsible unit" names in summaries | Directory `GET /api/v1/service-units` (cache briefly) or `/api/v1/validation/service-units/{id}` | `name`, `code` |
| Who staffs a unit (e.g. suggesting assignees) | Directory `GET /api/v1/responsibilities?service_unit_id={unit}&status=ACTIVE` | `data[].user_id`, `role_title` |

Example: may this service-desk officer triage requests for the synthetic IT help desk unit?

```
GET {identity}/api/v1/validation/users/usr-servicedesk-001/eligibility?required_role=SERVICE_DESK_OFFICER&relationship=RESPONSIBILITY&service_unit_id=unit-ithd-7fb5a0
```
`data.eligible: true` → allowed. `false` with `reasons: ["NO_MATCHING_RESPONSIBILITY"]` → show `data.message`.

Location/facility validation for requests comes from **Group 6**, not Group 5.

## 6. Group 8: Events, Communications and Feedback

*Assignment: "Consumes user/role/department data from Group 5." Announcements are targeted "by role, department, faculty, service unit, or all users".*

| When | Call | Use the result |
|---|---|---|
| Organizer creates or publishes an event | Identity `GET /api/v1/validation/users/{user_id}?required_role=EVENT_ORGANIZER` | Allow only if `is_valid` and `is_authorized` |
| Audience pickers (faculty, department, service unit) | Directory `GET /api/v1/faculties`, `/departments?faculty_id=`, `/service-units` (all support `?q=`) | Store the `id` or `code` in your AudienceRule / EventEligibility |
| Validating an audience rule when it is saved | Directory `/api/v1/validation/faculties/{id or code}`, `/validation/departments/{id or code}`, `/validation/service-units/{id or code}` | `404` → reject the rule |
| Registration restricted to a department or faculty | Identity `.../eligibility?relationship=AFFILIATION&department_id=` (or `faculty_id=`) | Register only if `data.eligible`; otherwise show `data.message` (the assignment requires "a clear explanation") |
| Resolving "all users in department D / faculty F" for a targeted announcement | Directory `GET /api/v1/affiliations?department_id={id}` or `?faculty_id={id}` | `data[].user_id`. Page with `skip`/`limit` (max 500 per page) |
| Resolving "all staff of service unit S" | Directory `GET /api/v1/responsibilities?service_unit_id={id}&status=ACTIVE` | `data[].user_id` |
| Targeting by role | Identity owns roles. `GET /api/v1/users` lists users but is restricted to ADMIN/STAFF, so **agree with the Identity team** how Group 8 resolves role audiences. For a single user, check `GET /api/v1/validation/users/{user_id}` → `data.roles` | |

**Checking visibility for one user** (e.g. "should this user see announcement A?") is cheaper per user than resolving the whole audience: call the Directory affiliation validation `GET /api/v1/validation/users/{user_id}/affiliation?department_id=` (`200` = in the audience, `404 AFFILIATION_NOT_FOUND` = not).

Venue validation for events comes from **Group 6**, not Group 5.

## 7. Shared frontend

| Page | Calls (all through the gateway base `/api/v1`) | Who may use it |
|---|---|---|
| `/auth` (login) | Identity `POST /auth/login` | everyone |
| `/profile` | Identity `GET /auth/me`, `GET /users/{id}` | the user |
| `/faculties` | Directory `GET/POST /faculties`, `GET/PUT/DELETE /faculties/{id}`, search `?q=` | read: any user; change: ADMIN |
| `/departments` | Directory `GET/POST /departments`, `GET/PUT/PATCH/DELETE /departments/{id}`, filter `?faculty_id=` | read: any user; change: ADMIN |
| `/service-units` | Directory `GET/POST /service-units`, `GET/PUT/DELETE /service-units/{id}` | read: any user; change: ADMIN |
| Affiliations admin | Directory `/affiliations` (create by university ID, e.g. `STU001`) | ADMIN |
| Responsibilities admin | Directory `/responsibilities` | ADMIN |

When wiring `apiFetch`:

- Read data from `body.data`, and errors from `body.error.message` / `body.error.code`.
- A delete can return `409 FACULTY_HAS_DEPENDENCIES`, `409 DEPARTMENT_HAS_DEPENDENCIES` or `409 SERVICE_UNIT_HAS_DEPENDENCIES`. Show the message: it says what to remove first.

## 8. API Gateway

Route by path without stripping a prefix; the full table is in [INTEGRATION.md](INTEGRATION.md#2-api-gateway-routes). The one trap is shared paths:

- `/api/v1/validation/users/{id}/affiliation` and `/api/v1/validation/users/{id}/responsibilities` go to the **Directory Service**.
- `/api/v1/validation/users/{id}` and `/api/v1/validation/users/{id}/eligibility` go to the **Identity Service**.

The gateway must forward the `Authorization` header.

## 9. Contacts and changes

- Directory Service: Pavithira Rajkumar (Group 5)
- Identity Service: Dayaleeswaran (Group 5)

Both contracts are `v1`. Adding response fields is not a breaking change, so ignore fields you don't recognise. Breaking changes will get a new version and will be announced before they ship.
