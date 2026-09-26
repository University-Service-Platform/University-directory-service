# University Directory Service

The Directory Service keeps the university's organisational structure. It owns faculties, departments, service units, user affiliations and service responsibilities. Other services call it to check that a faculty, department, service unit, affiliation or responsibility exists and is valid.

- Stack: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, httpx, PyJWT
- API base path: `/api/v1` (Swagger UI at `/docs`, ReDoc at `/redoc`, liveness at `/health`)
- Default port: `8002`
- Cross-service contract: [docs/API_CONTRACT.md](docs/API_CONTRACT.md)

## Service boundary

| Owned by the Directory Service | Owned by the Identity Service |
|---|---|
| Faculties, departments, service units | Users, profiles, credentials |
| User affiliations (user ↔ department/faculty) | Account status (ACTIVE / INACTIVE) |
| Service responsibilities (user ↔ unit/department/faculty) | Roles and authentication, token issuing |
| Directory validation endpoints | User validation |

Rules this service follows:

- It refers to users **only by `user_id`**. It never stores passwords, names, emails, roles or account status.
- It talks to the Identity Service **only over HTTP**, never through its database. The single call it makes today is
  `GET {IDENTITY_SERVICE_BASE_URL}/validation/users/{user_id}?require_active=true`.
- Service units are standalone. They are not part of the faculty → department hierarchy.
- Venue and facility validation (Group 6, facility-resource-service) is **out of scope**. This service has no integration with it.

## Project layout

```
app/
  auth/            token verification (pluggable) and role checks
  core/            error envelope, validators, UTC time, API versioning
  integrations/    Identity Service HTTP client
  models/          SQLAlchemy models
  repositories/    database access
  routes/          FastAPI routers (mounted under /api/v1)
  schemas/         Pydantic request/response models
  services/        business rules
  config.py        settings from environment variables
migrations/        Alembic migrations
tests/             pytest suite (no network access needed)
docs/              API contract
```

## Configuration

All configuration comes from environment variables; see [.env.example](.env.example). Copy it to `.env` for local use. `.env` is git-ignored and must never be committed.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./directory.db` | SQLAlchemy database URL |
| `IDENTITY_SERVICE_BASE_URL` | *(none)* | Identity Service base URL, no trailing slash. Needed for user checks and in `identity-hs256` mode. |
| `IDENTITY_TIMEOUT_CONNECT` | `3` | Connect timeout (seconds) for Identity calls |
| `IDENTITY_TIMEOUT_READ` | `5` | Read timeout (seconds) for Identity calls |
| `AUTH_MODE` | `identity-hs256` | `identity-hs256` (current) or `jwks` (target), see [Authentication](#authentication) |
| `JWT_SECRET_KEY` | *(none)* | `identity-hs256` only: must equal the Identity Service's `JWT_SECRET_KEY` |
| `JWT_ISSUER` | *(none)* | `jwks` only: expected `iss` |
| `JWT_AUDIENCE` | *(none)* | `jwks` only: expected `aud` |
| `JWKS_URL` | `{IDENTITY_SERVICE_BASE_URL}/.well-known/jwks.json` | `jwks` only: key set location |
| `JWKS_CACHE_TTL_SECONDS` | `300` | `jwks` only: key cache lifetime |

No URL, host or secret is hard-coded in the application. If the configuration needed by the selected auth mode is missing, protected requests fail closed with `500 AUTH_NOT_CONFIGURED`.

The API gateway base path is **to be confirmed**. The service does not assume one.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit values locally
```

## Database migrations

Alembic manages the schema. The app no longer creates tables at import time.

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

Then open http://localhost:8002/docs.

## Docker

```bash
docker build -t university-directory-service .
docker compose up --build        # uses docker-compose.yml; set variables in your shell or .env
```

- The image is based on `python:3.12-slim`, runs as a non-root `app` user, and stores SQLite data in the `/app/data` volume.
- On start the container runs `alembic upgrade head`, then uvicorn on port 8002.
- A `HEALTHCHECK` calls `/health`.
- `docker-compose.yml` requires `IDENTITY_SERVICE_BASE_URL`. The Identity Service is deployed separately; use e.g. `http://host.docker.internal:8001` when it runs on the host.

## Authentication

Every endpoint except `/health` requires `Authorization: Bearer <token>`. The token is issued by the Identity Service.

| Operation | Requirement |
|---|---|
| `GET` (reads and validation endpoints) | any valid token |
| `POST`, `PUT`, `PATCH`, `DELETE` | valid token **and** role `ADMIN` |

A missing, invalid or expired token returns `401 UNAUTHORIZED` (with `WWW-Authenticate: Bearer`). A token without the required role returns `403 FORBIDDEN`.

Token verification is pluggable (`app/auth/verifiers.py`). Both modes produce the same `Principal(user_id, roles)`, and the same authorization code (`require_roles("ADMIN")`) applies in both.

### `AUTH_MODE=identity-hs256` (current default)

This mode matches how the Identity Service works **today**:

- The Identity Service signs tokens with **HS256** using a shared `JWT_SECRET_KEY`.
- Its tokens carry `sub` and `exp` only, with **no `roles`, `iss` or `aud` claims**.
- The Directory Service checks the signature (with the same `JWT_SECRET_KEY`), `exp` and `sub`. It then calls the Identity validation endpoint for `sub`. That call confirms the user exists and is ACTIVE, and supplies their roles.
- Every protected request therefore makes one Identity call. If the Identity Service is down, requests fail closed (`503 IDENTITY_SERVICE_UNAVAILABLE`).

### `AUTH_MODE=jwks` (target contract)

This is the intended production contract. It needs no shared secret and no Identity call per request:

- RS256 signature checked against the Identity Service JWKS, with a cached key set that refreshes on key rotation
- `iss` = `JWT_ISSUER` (proposed `university-identity-service`)
- `aud` = `JWT_AUDIENCE` (proposed `university-services-platform`)
- `exp` and `sub` required; roles are read from the `roles` claim (a list of strings)

### Compatibility gap: the current Identity Service does NOT satisfy the JWKS contract

`jwks` mode will reject tokens issued by today's Identity Service. Before `jwks` can be used end to end, the Identity Service must:

1. Sign access tokens with **RS256** using a private key it keeps secret, instead of HS256 with a shared secret.
2. Publish its public key(s) at **`/.well-known/jwks.json`**, with a `kid` on each key and in each token header.
3. Add **`iss`** and **`aud`** claims matching the agreed values.
4. Add a **`roles`** claim (a list of role names such as `"ADMIN"`), or agree a different claim name.
5. Provide a way to obtain tokens. No token-issuing endpoint was found in the Identity Service code reviewed so far.

After that, set `AUTH_MODE=jwks` together with `JWT_ISSUER` and `JWT_AUDIENCE`; no code change is needed here. Until then, keep `identity-hs256` and treat `JWT_SECRET_KEY` as a secret.

## Identity Service integration

`app/integrations/identity_client.py` calls the existing Identity endpoint with configurable timeouts. It maps failures as follows:

| Identity outcome | Directory response |
|---|---|
| Timeout, connection error, base URL not set | `503 IDENTITY_SERVICE_UNAVAILABLE` |
| `404` | `404 USER_NOT_FOUND` |
| `403 ACCOUNT_INACTIVE`, or an inactive status in a 200 body | `409 USER_INACTIVE` |
| `5xx` or other unexpected status | `502 IDENTITY_SERVICE_ERROR` |
| Malformed JSON or unexpected body shape | `502 IDENTITY_SERVICE_BAD_RESPONSE` |

Downstream error text is logged and never returned to clients.

Where the Identity Service is called:

- **Affiliation create and update**: the user must exist and be ACTIVE.
- **Responsibility create and update**, whenever the resulting responsibility is ACTIVE. Deactivating or deleting a responsibility does not need the Identity Service, so records of users who have left can still be closed.
- Validation endpoints and reads use Directory data only.

## Data rules

- Deleting a faculty, department or service unit that still has dependent records returns **409** (`FACULTY_HAS_DEPENDENCIES`, `DEPARTMENT_HAS_DEPENDENCIES`, `SERVICE_UNIT_HAS_DEPENDENCIES`). Nothing is cascade-deleted. Foreign keys use `ON DELETE RESTRICT`.
- An ACTIVE responsibility must be unique per user and organisational scope (`409 RESPONSIBILITY_ALREADY_EXISTS`).
- Faculty, department and service-unit references accept an identifier or a code (codes are case-insensitive).
- Timestamps are generated in UTC. SQLite returns them without a UTC offset.

## API versioning

All routes live under `/api/v1`. The earlier unprefixed paths (`/faculties`, `/departments`, `/service-units`, `/affiliations`, `/validation/...`) still work as **deprecated aliases**:

- they are hidden from OpenAPI
- the same authentication rules apply
- responses carry `Deprecation: true` and a `Link` header pointing at the `/api/v1` successor

They will be removed once dependent services have migrated. `/responsibilities` exists only under `/api/v1`.

## Testing

```bash
pytest -q
```

The suite needs no network access:

- JWTs are signed with an RSA key generated in memory for each run, and the JWKS is mocked.
- The Identity Service is replaced by a fake (`tests/fakes.py`) or `httpx.MockTransport`.
- Every code, name and identifier in tests and documentation examples (e.g. `FSYN`, `DEPT-SYN`, `usr-syn-001`) is **synthetic** and does not describe real university data.
