"""The published docs/openapi.json must match the implementation."""
import json
import pathlib

from scripts.export_openapi import OUTPUT, render


def test_committed_openapi_matches_implementation():
    assert OUTPUT.exists(), "docs/openapi.json missing: run python scripts/export_openapi.py"
    committed = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert committed == json.loads(render()), "docs/openapi.json is stale: run python scripts/export_openapi.py"


def test_openapi_documents_versioned_api_and_bearer_auth():
    spec = json.loads(render())
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert all(p == "/health" or p.startswith("/api/v1/") for p in spec["paths"])
