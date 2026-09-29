# University Directory Service

[![CI](https://github.com/University-Service-Platform/University-directory-service/actions/workflows/ci.yml/badge.svg)](https://github.com/University-Service-Platform/University-directory-service/actions/workflows/ci.yml)

The Directory Service keeps the university's organisational structure. It owns faculties, departments, service units, user affiliations and service responsibilities. Other services call it to check that a faculty, department, service unit, affiliation or responsibility exists and is valid.

- Stack: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, httpx, PyJWT
- API base path: `/api/v1` (Swagger UI at `/docs`, ReDoc at `/redoc`, liveness at `/health`)
- Default port: `8002`
- Cross-service contract: [docs/API_CONTRACT.md](docs/API_CONTRACT.md)
- **Which API each team should use (Groups 6–8, frontend, gateway):** [docs/API_GUIDE_FOR_TEAMS.md](docs/API_GUIDE_FOR_TEAMS.md)
- OpenAPI document: [docs/openapi.json](docs/openapi.json)
- Postman collection: [docs/postman/](docs/postman/)
- Platform integration (Docker Compose, API Gateway, frontend notes): [docs/INTEGRATION.md](docs/INTEGRATION.md)

## Service boundary

| Owned by the Directory Service | Owned by the Identity Service |
|---|---|
| Faculties, departments, service units | Users, profiles, credentials |
| User affiliations (user ↔ department/faculty) | Account status (ACTIVE / INACTIVE) |
| Service responsibilities (user ↔ unit/department/faculty) | Roles, authentication and token issuing |
| Directory validation endpoints | User, role and eligibility validation |

Rules this service follows:

- It refers to users **only by the Identity `user_id`** (the JWT `sub`). It never stores passwords, names, emails, roles or account status.
- It talks to the Identity Service **only over HTTP**, never through its database. It uses the Identity API contract v1 (see [Identity Service integration](#identity-service-integration)).
- Service units are standalone. They are not part of the faculty → department hierarchy.
- Venue and facility validation (Group 6, facility-resource-service) is **out of scope**. This service has no integration with it.

## Project layout

```
app/
  auth/            token verification (pluggable) and role checks
  core/            error envelope, validators, UTC time, API versioning
  integrations/    Identity Service HTTP client
  models/          SQLAlchemy models
  repositories/    database access and search
  routes/          FastAPI routers (mounted under /api/v1)
  schemas/         Pydantic request/response models
  services/        business rules
  config.py        settings from environment variables
migrations/        Alembic migrations
scripts/           export_openapi.py
tests/             pytest suite (no network access needed)
docs/              API contract, OpenAPI document, Postman collection
```

## Configuration

All configuration comes from environment variables; see [.env.example](.env.example). Copy it to `.env` for local use. `.env` is git-ignored and must never be committed.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./directory.db` | SQLAlchemy database URL |
| `IDENTITY_SERVICE_BASE_URL` | *(none)* | Identity Service base URL, no trailing slash (e.g. `http://identity-service:8001` in Docker Compose). Required: used for signing keys, user checks and live role confirmation. |
| `IDENTITY_TIMEOUT_CONNECT` | `3` | Connect timeout (seconds) for Identity calls |
| `IDENTITY_TIMEOUT_READ` | `5` | Read timeout (seconds) for Identity calls |
| `AUTH_MODE` | `jwks` | `jwks` (Identity API contract v1) or `identity-hs256` (legacy), see [Authentication](#authentication) |
| `JWT_ISSUER` | `university-identity-service` | `jwks`: expected `iss` (contract value) |
| `JWT_AUDIENCE` | `university-services-platform` | `jwks`: expected `aud` (contract value) |
| `JWKS_URL` | `{IDENTITY_SERVICE_BASE_URL}/.well-known/jwks.json` | `jwks`: key set location |
| `JWKS_CACHE_TTL_SECONDS` | `300` | `jwks`: key cache lifetime |
| `JWT_SECRET_KEY` | *(none)* | `identity-hs256` only: the legacy Identity Service's shared secret. Leave empty otherwise. |

No URL, host or secret is hard-coded in the application. In the default `jwks` mode the service needs no secret at all. If the configuration needed by the selected auth mode is missing, protected requests fail closed with `500 AUTH_NOT_CONFIGURED`.

The API gateway base path is **to be confirmed**. The service does not assume one.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit values locally
```

## Database migrations

Alembic manages the schema. The app does not create tables at import time.

```bash
alembic upgrade head                                  # create/upgrade the schema
alembic revision --autogenerate -m "describe change"  # after changing models
alembic downgrade -1                                  # roll back one revision
```

`migrations/env.py` reads `DATABASE_URL` through `app/config.py`, so no connection string is stored in `alembic.ini`. On SQLite, foreign keys are enforced on every connection (`PRAGMA foreign_keys=ON`).

## Running

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Then open http://localhost:8002/docs. Use **Authorize** with an access token from the Identity Service (`POST /api/v1/auth/login`).

## Docker

```bash
docker build -t university-directory-service .
docker compose up --build        # uses docker-compose.yml; set variables in your shell or .env
```

- The image is based on `python:3.12-slim`, runs as a non-root `app` user, and stores SQLite data in the `/app/data` volume.
- On start the container runs `alembic upgrade head`, then uvicorn on port 8002.
- A `HEALTHCHECK` calls `/health`.
- `docker-compose.yml` requires `IDENTITY_SERVICE_BASE_URL`. The Identity Service is deployed separately. On a shared Compose network use `http://identity-service:8001`; when it runs on the host use `http://host.docker.internal:8001`.
- The image build and start-up are checked by the [CI workflow](#continuous-integration) on every pull request, so you don't need Docker installed locally to know the image works.
- For the shared platform Compose file and API Gateway routes, see [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Authentication

Every endpoint except `/health` requires `Authorization: Bearer <token>`, where the token is issued by the Identity Service (`POST /api/v1/auth/login`).

| Operation | Requirement |
|---|---|
| `GET` (reads, search and validation endpoints) | any valid token |
| `POST`, `PUT`, `PATCH`, `DELETE` | valid token **and** role `ADMIN`, confirmed live with the Identity Service |

- A missing, invalid or expired token returns `401 UNAUTHORIZED` (with `WWW-Authenticate: Bearer`).
- A token without the required role returns `403 FORBIDDEN`.

Token verification is pluggable (`app/auth/verifiers.py`). Both modes produce the same `Principal(user_id, roles)`, and the same authorization code (`require_roles("ADMIN")`) applies in both.

### `AUTH_MODE=jwks` (default; Identity API contract v1)

- **Signature:** RS256, checked against the Identity Service JWKS (`/.well-known/jwks.json`, keyed by the token's `kid`). The key set is cached and re-fetched when an unknown `kid` appears, so key rotation works.
- **Claims:** `iss` must be `university-identity-service`, `aud` must be `university-services-platform`, and `exp` and `sub` are required.
- **Roles:** taken from the `roles` claim. The Identity contract says these are a **login-time snapshot**: an administrator may change roles or deactivate the account after the token was issued.
- **Reads** need no Identity call.
- **Writes** re-confirm the caller's role live: `GET /api/v1/validation/users/{sub}?required_role=ADMIN`, forwarding the caller's token. The outcomes are:
  - role revoked after login: `403 FORBIDDEN`
  - account deactivated: `403 FORBIDDEN` ("Your account is not active.")
  - user deleted: `401 UNAUTHORIZED`
  - Identity Service down: `503 IDENTITY_SERVICE_UNAVAILABLE` (fails closed)

### `AUTH_MODE=identity-hs256` (legacy)

This mode exists only for the Sprint 1 Identity Service, which signed HS256 tokens with a shared `JWT_SECRET_KEY` and put no `roles`, `iss` or `aud` claims in them. Current Identity Service tokens are RS256 and do not verify in this mode.

In this mode the Directory Service checks the signature, `exp` and `sub`. It then calls the Identity validation endpoint on every request to confirm the caller is ACTIVE and to read their roles, so writes are not checked a second time. Don't use it with the v1 Identity Service.

## Identity Service integration

`app/integrations/identity_client.py` calls the Identity API contract v1 with configurable timeouts:

```
GET {IDENTITY_SERVICE_BASE_URL}/api/v1/validation/users/{user_id}[?required_role=ROLE]
Authorization: <the caller's own bearer token, forwarded>
```

`require_active` is deliberately not sent. An inactive **target** user is read from the response body (`is_valid: false`). That way a `403 ACCOUNT_INACTIVE` can only refer to the **caller's** own account.

| Identity outcome | Directory response |
|---|---|
| Timeout, connection error, base URL not set | `503 IDENTITY_SERVICE_UNAVAILABLE` |
| `404` | `404 USER_NOT_FOUND` |
| `200` with `is_valid: false` (target user inactive), when an active user is required | `409 USER_INACTIVE` |
| `401` (caller token rejected) | `401 UNAUTHORIZED` |
| `403 ACCOUNT_INACTIVE` (caller's account inactive) | `403 FORBIDDEN` |
| `5xx` or other unexpected status | `502 IDENTITY_SERVICE_ERROR` |
| Malformed JSON or unexpected body shape | `502 IDENTITY_SERVICE_BAD_RESPONSE` |

Downstream error text is logged and never returned to clients. Only `user_id`, `status`, `is_valid`, `roles` and `is_authorized` are read; profile fields are ignored.

Where the Identity Service is called:

- **Every write (jwks mode)**: to confirm the caller still holds `ADMIN` and is active.
- **Affiliation create and update**: the affiliated user must exist and be ACTIVE.
- **Responsibility create**: the user must exist, and must be ACTIVE if the responsibility is ACTIVE.
- **Responsibility update**: only when the result is ACTIVE. Deactivating or deleting makes no user check, so records of users who have left can still be closed.
- **Authentication in `identity-hs256` mode**: once per request.

Reads, search and validation endpoints otherwise answer from Directory data only. In particular, affiliation validation does not check the user's account status. For combined "role + relationship" decisions, dependent services should use the Identity Service's eligibility endpoint.

**User ids.** Writes accept an Identity user id or a university id (e.g. `STU001`). The Directory Service always stores the canonical Identity user id returned by the Identity Service (the JWT `sub`, e.g. `usr-student-001`), as the Identity contract requires. Reads and validation endpoints take that canonical id.

## Data rules

- Deleting a faculty, department or service unit that still has dependent records returns **409** (`FACULTY_HAS_DEPENDENCIES`, `DEPARTMENT_HAS_DEPENDENCIES`, `SERVICE_UNIT_HAS_DEPENDENCIES`). Nothing is cascade-deleted. Foreign keys use `ON DELETE RESTRICT`.
- An ACTIVE responsibility must be unique per user and organisational scope (`409 RESPONSIBILITY_ALREADY_EXISTS`).
- Faculty, department and service-unit references in paths and request bodies accept an identifier or a code (codes are case-insensitive). List filters and the responsibility-validation filters take identifiers only.
- `user_id` is at most 50 characters.
- List endpoints support `?q=` free-text search (case-insensitive substring, max 100 characters; `%` and `_` are matched literally):
  - faculties and service units: code, name and description
  - departments: code and name
  - affiliations: user id, and department and faculty code and name
  - responsibilities: user id, role title, and unit, department and faculty code and name
- Faculty, department and service-unit lists are ordered by code; affiliation lists by creation time.
- Timestamps are generated in UTC. SQLite returns them without a UTC offset.

## API versioning

All routes live under `/api/v1`. The earlier unprefixed paths (`/faculties`, `/departments`, `/service-units`, `/affiliations`, `/validation/...`) still work as **deprecated aliases**:

- they are hidden from OpenAPI
- the same authentication rules apply
- successful responses carry `Deprecation: true` and a `Link` header pointing at the `/api/v1` successor. Error responses from an alias (for example a 401) do not carry these headers.

They will be removed once dependent services have migrated. `/responsibilities` exists only under `/api/v1`.

## OpenAPI document

[docs/openapi.json](docs/openapi.json) is generated from the code. After any API change, run:

```bash
python scripts/export_openapi.py
```

`tests/test_openapi_spec.py` fails while the committed file is out of date.

## Testing

### Automated tests

```bash
pytest -q
```

The suite needs no network access:

- JWTs are signed with an RSA key generated in memory for each run, and the JWKS is mocked.
- The Identity Service is replaced by a fake (`tests/fakes.py`) or `httpx.MockTransport`.
- Every code, name and identifier in tests and documentation examples (e.g. `FSYN`, `DEPT-SYN`, `usr-syn-001`) is **synthetic** and does not describe real university data.

### Cross-service integration test

`tests/integration/` runs a real Identity ↔ Directory workflow against both services while they are running. It covers login, token verification, live ADMIN checks, affiliations, responsibilities and Identity eligibility calling back into the Directory Service.

It is skipped unless the `IT_*` environment variables are set. See [docs/INTEGRATION.md](docs/INTEGRATION.md#5-cross-service-integration-test) for how to run it:

```bash
pytest -m integration tests/integration -v
```

### Continuous integration

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs on every pull request, on every push to `main`, and on demand (**Actions** → **CI** → **Run workflow**). It has two jobs:

- **Tests (pytest):** installs `requirements-dev.txt` and runs the full suite. It also confirms `docs/openapi.json` is up to date and uploads the JUnit report as an artifact.
- **Docker build and smoke test:**
  - builds the image and starts it with `docker compose up --wait` (the container must report healthy)
  - checks `/health`, `/docs` and `/openapi.json`
  - checks that `/api/v1/faculties` without a token returns `401 UNAUTHORIZED`
  - checks that the container runs as the non-root `app` user
  - checks that Alembic migrations reached `head`

  It needs no real Identity Service.

Results appear on the pull request's **Checks** tab and on the repository's **Actions** tab.

### Postman / newman

`docs/postman/` contains a collection (10 folders, 49 requests) and a local environment template. It logs in through the Identity Service, then exercises every Directory endpoint, the error cases, the 409 delete protection and cleanup. All data it creates is synthetic, suffixed per run and removed at the end.

1. Start the Identity Service and the Directory Service, with the Directory Service's `IDENTITY_SERVICE_BASE_URL` pointing at the Identity Service.
2. Fill in the environment locally, and **do not commit credentials**:
   - `adminUsername` / `adminPassword`: a synthetic ADMIN account
   - `staffUsername` / `staffPassword`: a synthetic non-admin account
   - `affiliationUserId`: e.g. a student's university id
   - `responsibleUserId`: e.g. a service desk officer's university id
3. Run it in Postman (folders in order), or from the command line:

```bash
npx newman run docs/postman/directory-service.postman_collection.json \
  -e docs/postman/directory-service.local.postman_environment.json \
  --env-var adminPassword=... --env-var staffPassword=... \
  --reporters cli,json --reporter-json-export newman-report.json
```

Keep the newman report as test execution evidence.
