# Directory Service documentation

| Document | What it's for | Main readers |
|---|---|---|
| [API_CONTRACT.md](API_CONTRACT.md) | The API reference: every endpoint with auth, request, response, status codes, error codes and verified JSON examples | All API consumers |
| [API_GUIDE_FOR_TEAMS.md](API_GUIDE_FOR_TEAMS.md) | Which Group 5 endpoint each team should call, and when | Groups 6, 7, 8, frontend, gateway |
| [openapi.json](openapi.json) | Machine-readable OpenAPI 3.1 document, generated from the code (`python scripts/export_openapi.py`) | Tools, code generators, Swagger |
| [postman/](postman/) | Postman collection (49 requests) and local environment template | Testers, other teams |
| [INTEGRATION.md](INTEGRATION.md) | Shared Docker Compose entry, API Gateway routes, frontend notes, cross-service integration test | Integration Council, DevOps |
| [../README.md](../README.md) | Setup, configuration, migrations, running, Docker, authentication, testing | Developers of this service |

The live, interactive version of the API reference is the Swagger UI at `{base}/docs` on any running instance.

**Keeping the docs accurate.** CI fails when:

- `docs/openapi.json` no longer matches the code (`tests/test_openapi_spec.py`)
- an implemented operation is missing from the endpoint summary in `API_CONTRACT.md`, or an error code the code can return is missing from its error index (`tests/test_api_docs.py`)

The JSON examples in `API_CONTRACT.md` were captured from the running service with synthetic data.
