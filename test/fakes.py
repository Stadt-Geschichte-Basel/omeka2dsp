"""A fake requests.Session that records the requests and returns set responses."""

import json
from typing import Any

from omeka2dsp.dsp import Dsp
from omeka2dsp.settings import Settings

SETTINGS = Settings(
    _env_file=None,
    api_host="https://api.test.com",
    ingest_host="https://ingest.test.com",
    project_short_code="TEST",
    dsp_user="user@test.com",
    dsp_pwd="secret",
)


class Response:
    def __init__(self, status: int = 200, data: Any = None, content: bytes = b""):
        self.status_code, self._data, self.content = status, data, content
        self.text = json.dumps(data) if data is not None else ""
        self.links: dict = {}

    def json(self) -> Any:
        if self._data is None:
            raise ValueError("no JSON body")
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Session:
    """Answer each request with the first matching (method, URL part) response."""

    def __init__(self, routes: dict[tuple[str, str], Response] | None = None):
        self.routes = routes or {}
        self.sent: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kw: Any) -> Response:
        self.sent.append({"method": method, "url": url, **kw})
        for (m, part), response in self.routes.items():
            if m == method and part in url:
                return response
        return Response(200, {})

    def get(self, url: str, **kw: Any) -> Response:
        return self.request("GET", url, **kw)


def dsp(routes=None) -> tuple[Dsp, Session]:
    session = Session(routes)
    return Dsp(SETTINGS, session, "token"), session
