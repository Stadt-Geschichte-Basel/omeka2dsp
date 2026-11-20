"""A requests transport that records requests and returns set responses."""

import json
from typing import Any

import requests
from requests.adapters import BaseAdapter

from omeka2dsp.dsp import Dsp
from omeka2dsp.settings import Settings

SETTINGS = Settings(
    _env_file=None,
    api_host="https://api.test.com",
    ingest_host="https://ingest.test.com",
    project_short_code="TEST",
    dsp_user="user@test.com",
    dsp_pwd="secret",
    ontology_name="SGB",
    item_set_id="10780",
    omeka_api_url="https://omeka.test.com/api/",
    key_identity=None,
    key_credential=None,
    http_timeout=30,
)

Route = tuple[str, str]


def response(status: int = 200, data: Any = None, next_url: str | None = None) -> dict:
    return {"status": status, "data": data, "next": next_url}


class Transport(BaseAdapter):
    """Answer each request with the first route whose method and URL part match."""

    def __init__(self, routes: dict[Route, dict]):
        super().__init__()
        self.routes = routes
        self.sent: list[dict[str, Any]] = []

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        body = request.body
        if (
            isinstance(body, bytes)
            and request.headers.get("Content-Type") == "application/json"
        ):
            body = json.loads(body)
        self.sent.append(
            {
                "method": request.method,
                "url": request.url,
                "body": body,
                "timeout": timeout,
            }
        )
        answer = next(
            (
                r
                for (method, part), r in self.routes.items()
                if method == request.method and part in (request.url or "")
            ),
            response(200, {}),
        )
        result = requests.Response()
        result.status_code = answer["status"]
        result._content = json.dumps(answer["data"]).encode()
        result.encoding = "utf-8"
        result.url = request.url or ""
        result.request = request
        if answer["next"]:
            result.headers["link"] = f'<{answer["next"]}>; rel="next"'
        return result

    def close(self) -> None:
        pass


def session(
    routes: dict[Route, dict] | None = None,
) -> tuple[requests.Session, Transport]:
    transport = Transport(routes or {})
    http = requests.Session()
    http.mount("https://", transport)
    return http, transport


def dsp(routes: dict[Route, dict] | None = None) -> tuple[Dsp, Transport]:
    http, transport = session(routes)
    return Dsp(SETTINGS, http, "token"), transport
