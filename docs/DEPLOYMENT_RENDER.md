# Deploying the Directory Service on Render

## Current deployment

| Item | Value |
|---|---|
| Service URL | `https://university-directory-service.onrender.com` |
| Swagger UI | `https://university-directory-service.onrender.com/docs` |
| Health check | `https://university-directory-service.onrender.com/health` |
| Platform | Render web service, **Free** instance, region **Singapore**, built from `./Dockerfile` on `main` |
| Database | PostgreSQL on **Neon** (free plan, AWS Singapore), direct connection (not the pooled `-pooler` host) |
| Deploys | Manual: Render has no GitHub app access to the organisation, so after changes are merged use **Manual Deploy → Deploy latest commit** |
| `IDENTITY_SERVICE_BASE_URL` | *placeholder until the Identity Service is hosted*; API calls with a token return `503 IDENTITY_SERVICE_UNAVAILABLE` until it is set |

Verified after deployment (30 September 2026):

- `/health` returned `200`
- `/docs` returned `200`
- `/openapi.json` listed all 33 operations
- `/api/v1/faculties` without a token, or with an invalid token, returned `401 UNAUTHORIZED`

The deployment below was done with the **manual web service + Neon** path (see [Alternative](#alternative-render-web-service--neon-postgresql)). The Blueprint is kept for teams that can use Render's own PostgreSQL.

## Deploy with the Blueprint

This deploys the service from GitHub with the Blueprint in [`render.yaml`](../render.yaml). It creates:

| Render resource | What it is |
|---|---|
| `university-directory-service` | Docker web service built from `./Dockerfile` (free plan, Singapore region) |
| `university-directory-db` | PostgreSQL database; its connection string is injected as `DATABASE_URL` |

The container runs `alembic upgrade head` on every start, so the database schema is created and upgraded automatically.

## Before you start

1. **A Render account.** Sign up at https://render.com with **GitHub**.
2. **Access to the repository.** When Render asks which repositories it may see, allow `University-Service-Platform/University-directory-service`.
   - If the repository doesn't appear, an **owner of the University-Service-Platform organisation** has to approve the Render GitHub app for the organisation (GitHub → organisation **Settings** → **GitHub Apps**).
3. **The Identity Service URL.** The Directory Service needs the Identity Service to verify tokens, so the Identity Service must be deployed too, for example on Render by the Identity team. You'll need its public URL, e.g. `https://university-identity-service.onrender.com`.
   - Without it, the Directory Service starts and `/health` works, but every API call needing a token fails safely (`503`).

## Deploy (Blueprint)

1. In the Render dashboard, click **New** → **Blueprint**.
2. Select the repository `University-directory-service` and branch `main`.
3. Render reads `render.yaml` and shows the web service and the database. When asked for **`IDENTITY_SERVICE_BASE_URL`**, enter the Identity Service's URL with no trailing slash.
4. Click **Apply** (or **Deploy Blueprint**). The first build takes a few minutes; you can watch it under the service's **Logs**.
5. When the service shows **Live**, open:
   - `https://<your-service>.onrender.com/health` should return `{"status": "healthy", ...}`
   - `https://<your-service>.onrender.com/docs` shows the Swagger UI with the `/api/v1` routes
   - `https://<your-service>.onrender.com/api/v1/faculties` without a token should return `401 UNAUTHORIZED`, which is correct

The exact service URL is shown at the top of the service page in Render.

After this, every push to `main` redeploys automatically.

## Check it works end to end

With the Identity Service deployed:

1. Log in at the Identity Service: `POST https://<identity>/api/v1/auth/login` with a synthetic demo account (e.g. ADM001).
2. In the Directory Swagger UI (`/docs`), click **Authorize** and paste the `access_token`.
3. Create a faculty (`POST /api/v1/faculties`), then list faculties.

Or run the Postman collection against the hosted services. Set `directoryBaseUrl` and `identityBaseUrl` to the Render URLs; see the README section "Postman / newman".

## Things to know about Render's free plan

These limits were current when this was written; check Render's documentation for the latest.

- **Sleeping:** free web services stop after about 15 minutes without traffic. The next request takes up to about a minute while the service starts again. Before a demo, open `/health` on **both** the Identity and Directory services to wake them. The Blueprint sets long Identity timeouts (`IDENTITY_TIMEOUT_READ=60`) so a waking Identity Service doesn't cause 503s.
- **Free PostgreSQL is time-limited:** free Render databases expire after a fixed period (30 days at the time of writing). Note the expiry date in the database's page and plan the final demo around it, or upgrade the database plan.
- **No persistent disk:** this is why the Blueprint uses PostgreSQL instead of the SQLite default.
- **Data:** only synthetic data. Never load real student or staff records.

## Configuration on Render

| Variable | Set by | Value |
|---|---|---|
| `DATABASE_URL` | Render (from the database) | PostgreSQL connection string (secret, never committed) |
| `IDENTITY_SERVICE_BASE_URL` | You, in the dashboard | Identity Service public URL |
| `AUTH_MODE` | `render.yaml` | `jwks` |
| `IDENTITY_TIMEOUT_CONNECT` / `IDENTITY_TIMEOUT_READ` | `render.yaml` | `10` / `60` |
| `PORT` | Render | Render sets it; the container listens on it |

To change a value later: service page → **Environment** → edit → **Save changes**. The service redeploys.

## Alternative: Render web service + Neon PostgreSQL

This is how the current deployment was made. It avoids creating a Render database (Render asked for card verification; note that it did so even for the free web service).

1. **Neon:** create a free project (region **AWS Asia Pacific (Singapore)**, the same as the Render service).
   - Open **Connect**, switch **Connection pooling off** (the host must not contain `-pooler`) and copy the connection string.
   - The string contains the database password. Keep it only in Render's settings, never in Git, documents or screenshots.
2. **Render → New → Web Service:**
   - connect the repository
   - **Language** Docker, **Branch** `main`, **Region** Singapore, **Instance** Free (check the summary shows **$0 / month**)
3. **Environment variables:**

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string (keep `?sslmode=require&channel_binding=require`) |
   | `IDENTITY_SERVICE_BASE_URL` | the Identity Service URL, with no trailing `/` |
   | `IDENTITY_TIMEOUT_CONNECT` | `10` |
   | `IDENTITY_TIMEOUT_READ` | `60` |

   The service turns `postgresql://` into the psycopg 3 driver URL itself.
4. **Advanced → Health Check Path:** `/health`, then **Deploy Web Service**.

**Changing the database password later:**

1. In Neon, open **Connect → Reset password** and copy the new string (pooling off).
2. In Render, open the service **Environment**, edit `DATABASE_URL`, then **Save changes**. The service redeploys.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Build fails | Open **Logs** for the failing deploy. The same Docker build runs in GitHub CI on every pull request, so compare with the **Docker build and smoke test** job there. |
| `/health` works, but API calls return `503 IDENTITY_SERVICE_UNAVAILABLE` | `IDENTITY_SERVICE_BASE_URL` is wrong or the Identity Service is down or asleep. Open `<identity>/health` and `<identity>/.well-known/jwks.json` in a browser. |
| API calls return `401 UNAUTHORIZED` with a valid-looking token | The token was issued by a different Identity deployment, or it expired (60 minutes). Log in again at the same Identity Service that `IDENTITY_SERVICE_BASE_URL` points to. |
| Data disappeared | The free database expired, or a new Blueprint created a new database. Check the database page in Render. |
| Deploy fails during `alembic upgrade head` | Check the database is **Available** and `DATABASE_URL` is set on the service. |
