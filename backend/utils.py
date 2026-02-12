"""Backend utilities."""

import os

from starlette.requests import Request


def get_base_url(request: Request) -> str:
    """
    Build base URL from request, respecting X-Forwarded-* headers (nginx).
    When BASE_URL is set (e.g. for path-based deployment like /archive-to-video/app),
    use that so OAuth redirects and callbacks work correctly.
    """
    base_url = os.environ.get("BASE_URL")
    if base_url:
        return base_url.rstrip("/")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    forwarded_host = request.headers.get("X-Forwarded-Host", request.url.hostname or "localhost")
    port = request.url.port
    if forwarded_host and ":" not in str(forwarded_host) and port and port not in (80, 443):
        return f"{forwarded_proto}://{forwarded_host}:{port}"
    return f"{forwarded_proto}://{forwarded_host}"
