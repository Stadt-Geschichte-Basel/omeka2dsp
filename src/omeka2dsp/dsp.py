"""DSP API client: login, search, read, create, change, erase, ingest."""

import logging
import urllib.parse
from dataclasses import dataclass, replace
from typing import Any, Literal, Protocol

from omeka2dsp.fields import Project
from omeka2dsp.settings import Settings

log = logging.getLogger(__name__)

JsonLd = dict[str, Any]


class HttpResponse(Protocol):
    """The part of requests.Response that the clients use."""

    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    @property
    def links(self) -> dict: ...

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class HttpSession(Protocol):
    """The part of requests.Session that the clients use."""

    def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse: ...

    def get(self, url: str, **kwargs: Any) -> HttpResponse: ...


class DspError(RuntimeError):
    """A DSP request that did not return status 200."""


def quote(iri: str) -> str:
    return urllib.parse.quote(iri, safe="")


@dataclass(frozen=True)
class Dsp:
    settings: Settings
    session: HttpSession
    token: str = ""

    def _send(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        host: str | None = None,
        **kw,
    ) -> HttpResponse:
        headers = {**kw.pop("headers", {})}
        if auth:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self.session.request(
            method,
            f"{host or self.settings.api_host}{path}",
            headers=headers,
            timeout=self.settings.http_timeout,
            **kw,
        )
        if response.status_code != 200:
            raise DspError(f"{response.status_code}: {response.text}")
        return response

    @classmethod
    def login(cls, settings: Settings, session: HttpSession) -> "Dsp":
        credentials = {
            "email": settings.dsp_user,
            "password": settings.dsp_pwd.get_secret_value(),
        }
        dsp = cls(settings, session)
        response = dsp._send("POST", "/v2/authentication", auth=False, json=credentials)
        log.info("Login successful")
        return replace(dsp, token=response.json()["token"])

    def project(self) -> Project:
        code = self.settings.project_short_code
        response = self.session.get(
            f"{self.settings.api_host}/admin/projects/shortcode/{code}",
            timeout=self.settings.http_timeout,
        )
        data = response.json()["project"]
        iri = data["id"]
        log.info(f"project Iri: {iri}")
        name = self.settings.ontology_name
        ontologies = data.get("ontologies") or [
            f"{self.settings.api_host}/ontology/{code}/{name}/v2"
        ]
        return Project(
            iri=iri,
            shortcode=code,
            ontology_name=name,
            ontology_iri=ontologies[0].rstrip("#"),
        )

    def lists(self, project: Project) -> list[JsonLd]:
        """All project lists. A failed request stops the run.

        A missing list would turn each lookup into a deletion.
        """
        index = self._send(
            "GET", "/admin/lists/", auth=False, params={"projectIri": project.iri}
        )
        lists = [
            self._send("GET", f"/v2/lists/{quote(item['id'])}", auth=False).json()
            for item in index.json()["lists"]
        ]
        log.info("Got Lists from project")
        return lists

    def ontology(self, project: Project) -> JsonLd:
        path = f"/v2/ontologies/allentities/{quote(project.ontology_iri)}"
        return self._send("GET", path).json()

    def ontology_metadata(self, project: Project) -> JsonLd:
        return self._send("GET", f"/v2/ontologies/metadata/{quote(project.iri)}").json()

    def create_class(self, body: JsonLd) -> JsonLd:
        return self._send("POST", "/v2/ontologies/classes", json=body).json()

    def find(
        self, project: Project, resource_class: str, identifier: str
    ) -> str | None:
        """The IRI of the resource in this class with this identifier."""
        p = project.prefix
        literal = identifier.replace("\\", "\\\\").replace('"', '\\"')
        query = f"""
            PREFIX knora-api: <http://api.knora.org/ontology/knora-api/v2#>
            PREFIX {p} <{project.ontology_iri}#>
            CONSTRUCT {{
                ?metadata knora-api:isMainResource true .
                ?metadata {p}hasIdentifier ?identifierValue .
                ?metadata {p}hasTitle ?title .
            }} WHERE {{
                ?metadata a {resource_class} .
                ?metadata {p}hasIdentifier ?identifierValue .
                ?identifierValue knora-api:valueAsString ?identifier .
                ?metadata {p}hasTitle ?title .
                FILTER(?identifier = "{literal}")
            }}
            """
        try:
            response = self._send(
                "POST",
                "/v2/searchextended",
                data=query.encode("utf-8"),
                headers={"Content-Type": "application/sparql-query; charset=utf-8"},
            )
        except DspError as error:
            log.error(f"Error: {error}")
            return None
        return response.json().get("@id")

    def resource(self, iri: str) -> JsonLd:
        response = self.session.get(
            f"{self.settings.api_host}/v2/resources/{quote(iri)}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self.settings.http_timeout,
        )
        return response.json()

    def create(self, body: JsonLd) -> str | None:
        """Create a resource. Return its IRI."""
        headers = {"X-Asset-Ingested": "true"}
        return (
            self._send("POST", "/v2/resources", json=body, headers=headers)
            .json()
            .get("@id")
        )

    def change(
        self, action: Literal["create", "update", "delete"], body: JsonLd
    ) -> None:
        headers = {"X-Asset-Ingested": "true"}
        if action == "delete":
            self._send("POST", "/v2/values/delete", json=body, headers=headers)
        else:
            method = "PUT" if action == "update" else "POST"
            self._send(method, "/v2/values", json=body, headers=headers)

    def restrict(self, body: JsonLd) -> None:
        self._send("PUT", "/v2/values", json=body)

    def erase(self, body: JsonLd) -> None:
        """Erase a resource and its file. This needs project-admin rights."""
        self._send("POST", "/v2/resources/erase", json=body)

    def download(self, url: str) -> bytes:
        response = self.session.get(url, timeout=self.settings.http_timeout)
        response.raise_for_status()
        return response.content

    def ingest(self, filename: str, content: bytes) -> str:
        """Upload a file to the ingest service. Return the internal file name."""
        code = self.settings.project_short_code
        response = self._send(
            "POST",
            f"/projects/{code}/assets/ingest/{urllib.parse.quote(filename)}",
            host=self.settings.ingest_host,
            data=content,
            headers={"Content-Type": "application/octet-stream"},
        )
        return response.json()["internalFilename"]
