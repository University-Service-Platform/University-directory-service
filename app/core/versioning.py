from fastapi import Request, Response

API_V1_PREFIX = "/api/v1"


def mark_legacy_route(request: Request, response: Response) -> None:
    """Dependency for unprefixed aliases kept while other teams migrate to /api/v1."""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'<{API_V1_PREFIX}{request.url.path}>; rel="successor-version"'
