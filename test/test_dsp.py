import pytest

from fakes import SETTINGS, Response, Session
from omeka2dsp.dsp import Dsp, DspError
from omeka2dsp.fields import Project

PROJECT = Project(iri="p", shortcode="TEST", ontology_name="SGB", ontology_iri="o")


def test_login_keeps_the_token():
    session = Session({("POST", "/v2/authentication"): Response(200, {"token": "t"})})
    client = Dsp.login(SETTINGS, session)
    assert client.token == "t"
    assert session.sent[0]["json"]["password"] == "secret"


def test_failed_list_request_stops_the_run():
    """Safety rule 5."""
    session = Session(
        {
            ("GET", "/admin/lists/"): Response(200, {"lists": [{"id": "l1"}]}),
            ("GET", "/v2/lists/"): Response(500),
        }
    )
    client = Dsp(SETTINGS, session, "t")
    with pytest.raises(DspError):
        client.lists(PROJECT)


def test_all_requests_use_the_timeout():
    session = Session()
    client = Dsp(SETTINGS, session, "t")
    client.change("delete", {})
    client.ontology(PROJECT)
    assert {r["timeout"] for r in session.sent} == {SETTINGS.http_timeout}
    assert session.sent[0]["url"].endswith("/v2/values/delete")
