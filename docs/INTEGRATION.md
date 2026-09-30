# Directory Service: Platform Integration Guide

**Audience:** the Project Integration Council (shared Docker Compose and API Gateway), the shared frontend team, and the Identity Service (Group 5).

This page describes what the platform needs in order to run the Directory Service alongside the other services. The API itself is specified in [API_CONTRACT.md](API_CONTRACT.md).

**Current hosted instance:** `https://university-directory-service.onrender.com` (Render, Singapore; PostgreSQL on Neon). See [DEPLOYMENT_RENDER.md](DEPLOYMENT_RENDER.md#current-deployment). It becomes fully usable once `IDENTITY_SERVICE_BASE_URL` points at the hosted Identity Service.

## 1. Shared Docker Compose entry

The Directory Service needs one other service at runtime, the **Identity Service**. It fetches the Identity signing keys (JWKS) to verify tokens and calls the Identity validation API. The Identity Service in turn calls the Directory Service for eligibility checks. Both calls are made per request, so either service can start first.

```yaml
services:
  identity-service:
    build: ../University-identity-service
    ports: ["8001:8001"]
    environment:
      DIRECTORY_SERVICE_BASE_URL: http://directory-service:8002
      DEMO_USER_PASSWORD: ${DEMO_USER_PASSWORD:?set a local demo password}
      # For stable tokens across restarts, mount RS256 keys and set
      # JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH (see the Identity README).

  directory-service:
    build: ../University-directory-service
    ports: ["8002:8002"]
    environment:
      IDENTITY_SERVICE_BASE_URL: http://identity-service:8001
      # AUTH_MODE defaults to jwks; JWT_ISSUER / JWT_AUDIENCE default to the Identity contract values.
    volumes:
      - directory-data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=4)"]
      interval: 30s
      timeout: 5s
      start_period: 15s
      retries: 3

volumes:
  directory-data:
```

- The image runs `alembic upgrade head` on start. It needs no secrets.
- Tokens are verified against the Identity JWKS, which is cached and re-fetched automatically when the Identity Service rotates or regenerates its key.
- This snippet has **not yet been run with Docker**: Docker was unavailable in the development environment. The same two services were run together without Docker (see section 5).

## 2. API Gateway routes

The shared frontend calls every service through one base path, `VITE_API_BASE_URL=/api/v1` (for example `GET /api/v1/faculties`). The gateway therefore routes **by path, without stripping a prefix**, and the Directory Service serves exactly these paths:

| Path pattern (under the gateway) | Service |
|---|---|
| `/api/v1/faculties`, `/api/v1/faculties/**` | Directory |
| `/api/v1/departments`, `/api/v1/departments/**` | Directory |
| `/api/v1/service-units`, `/api/v1/service-units/**` | Directory |
| `/api/v1/affiliations`, `/api/v1/affiliations/**` | Directory |
| `/api/v1/responsibilities`, `/api/v1/responsibilities/**` | Directory |
| `/api/v1/validation/faculties/**`, `/api/v1/validation/departments/**`, `/api/v1/validation/service-units/**` | Directory |
| `/api/v1/validation/users/{id}/affiliation` | Directory |
| `/api/v1/validation/users/{id}/responsibilities` | Directory |
| `/api/v1/validation/users/{id}` and `/api/v1/validation/users/{id}/eligibility` | **Identity** |
| `/api/v1/auth/**`, `/api/v1/users/**`, `/api/v1/roles/**`, `/api/v1/audit-logs` | Identity |

**Watch out: `/api/v1/validation/users/...` is shared.** A prefix rule such as `/api/v1/validation/users/** → identity` would send the Directory's `/affiliation` and `/responsibilities` checks to the wrong service. Route those two suffixes to the Directory Service **before** the Identity rule, for example with a regex such as `^/api/v1/validation/users/[^/]+/(affiliation|responsibilities)$`.

Gateway requirements:

- Forward the `Authorization` header unchanged. Every Directory endpoint except `/health` needs it.
- Forward or generate `X-Request-ID`, as the Identity Service does, so a request can be traced across services.
- `/health` is public, and is served at the service root (`GET {directory}/health`).
- **CORS is not needed** when the browser only talks to the gateway on the same origin, which is the case for the shared frontend.

## 3. Notes for the shared frontend

The frontend placeholders in `src/services/facultyService.ts` and `serviceUnitService.ts` already use the right paths (`/faculties`, `/service-units` under `/api/v1`). When wiring them:

- **Success responses** are `{"success": true, "data": ...}`. `apiFetch` returns the whole body as `data`, so read `response.data.data`.
- **Error responses** are `{"success": false, "error": {"code", "message"}}`. `apiFetch` currently reads `body.message`, so read `body.error.message` instead, and branch on `body.error.code`.
- **Searching:** list endpoints accept `?q=` (e.g. `GET /api/v1/faculties?q=science`), so the search box can query the server instead of filtering locally.
- **Tokens:** send the Identity access token as `Authorization: Bearer <token>` on every request. Only ADMIN can create, update or delete. The server enforces this (`403 FORBIDDEN`), so hiding buttons is for convenience only.
- **Other responses to handle:**
  - `409` codes such as `FACULTY_HAS_DEPENDENCIES` explain why a delete was refused.
  - `503 IDENTITY_SERVICE_UNAVAILABLE` means "try again later".

## 4. Notes for the Identity Service

Section 5 of [API_CONTRACT.md](API_CONTRACT.md) lists how the Identity Service should call the Directory Service. The most important point is to use `GET /api/v1/validation/users/{id}/affiliation?department_id=&faculty_id=` for affiliation eligibility. `GET /affiliations/users/{id}` returns only a user's first affiliation, so a student affiliated with two departments can be wrongly reported as not affiliated with the second.

## 5. Cross-service integration test

`tests/integration/test_identity_directory_workflow.py` runs a full workflow against **real, running** Identity and Directory services:

1. an admin logs in at the Identity Service
2. the Directory Service accepts the token and confirms ADMIN live
3. the admin creates a faculty, department and service unit
4. the admin affiliates a student by university ID, and the canonical user ID is stored
5. the admin assigns a responsibility
6. the Identity eligibility endpoint calls back into the Directory Service and reports the correct results
7. the test checks rejection of non-admin writes and of inactive users
8. the test checks delete protection
9. the test cleans up everything it created

It is skipped in the normal `pytest` run. To run it:

```bash
# Identity (repo University-identity-service):
#   alembic upgrade head && DEMO_USER_PASSWORD=<local> python -m app.seed --demo
#   DIRECTORY_SERVICE_BASE_URL=http://localhost:8002 uvicorn app.main:app --port 8001
# Directory (this repo):
#   alembic upgrade head && IDENTITY_SERVICE_BASE_URL=http://localhost:8001 uvicorn app.main:app --port 8002

export IT_DIRECTORY_BASE_URL=http://localhost:8002 IT_IDENTITY_BASE_URL=http://localhost:8001
export IT_ADMIN_USERNAME=ADM001 IT_STAFF_USERNAME=STF001 IT_STUDENT_USERNAME=STU001
export IT_RESPONSIBLE_USERNAME=SDO001 IT_INACTIVE_USERNAME=STU002
export IT_ADMIN_PASSWORD=<local demo password> IT_STAFF_PASSWORD=<local demo password>
pytest -m integration tests/integration -v
```

**Last verified:** 2026-09-30, against the Identity Service `main` branch (commit `58ffa9d`) with its synthetic demo users.

- The integration test passed.
- The Postman collection passed: 49 requests, 86 assertions, 0 failures.
- The services were run directly with Python, not in Docker.
