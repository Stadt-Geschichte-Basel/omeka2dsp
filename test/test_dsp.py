import pytest

from fakes import SETTINGS, response, session
from omeka2dsp.dsp import Dsp, DspError
from omeka2dsp.fields import Project

PROJECT = Project(iri="p", shortcode="TEST", ontology_name="SGB", ontology_iri="o")


def test_login_keeps_the_token():
    http, transport = session(
        {("POST", "/v2/authentication"): response(200, {"token": "t"})}
    )
    assert Dsp.login(SETTINGS, http).token == "t"
    assert transport.sent[0]["body"]["password"] == "secret"


def test_failed_list_request_stops_the_run():
    """Safety rule 5."""
    http, _ = session(
        {
            ("GET", "/admin/lists/"): response(200, {"lists": [{"id": "l1"}]}),
            ("GET", "/v2/lists/"): response(500),
        }
    )
    with pytest.raises(DspError):
        Dsp(SETTINGS, http, "t").lists(PROJECT)


def test_all_requests_use_the_timeout():
    http, transport = session()
    client = Dsp(SETTINGS, http, "t")
    client.change("delete", {})
    client.ontology(PROJECT)
    assert {r["timeout"] for r in transport.sent} == {SETTINGS.http_timeout}
    assert transport.sent[0]["url"].endswith("/v2/values/delete")


def test_search_escapes_the_identifier():
    http, transport = session(
        {("POST", "/searchextended"): response(200, {"@id": "iri"})}
    )
    assert Dsp(SETTINGS, http, "t").find(PROJECT, "SGB:Parent", 'a"b') == "iri"
    assert 'FILTER(?identifier = "a\\"b")' in transport.sent[0]["body"].decode()


@pytest.mark.parametrize(
    ("method", "part", "call"),
    [
        ("GET", "/admin/projects/", lambda dsp: dsp.project()),
        ("GET", "/v2/resources/", lambda dsp: dsp.resource("iri")),
        ("POST", "/searchextended", lambda dsp: dsp.find(PROJECT, "SGB:Parent", "x")),
    ],
)
def test_reads_check_the_status_first(method, part, call):
    """An error body is not read as data, and a failed search is not "not found"."""
    http, _ = session({(method, part): response(500, {"project": {"id": "p"}})})
    with pytest.raises(DspError):
        call(Dsp(SETTINGS, http, "t"))


def project_session(ontologies):
    data = {"project": {"id": "p", "ontologies": ontologies}}
    return session({("GET", "/admin/projects/"): response(200, data)})[0]


def test_project_takes_the_configured_ontology():
    other, sgb = "http://x/ontology/4001/Other/v2", "http://x/ontology/4001/SGB/v2"
    project = Dsp(SETTINGS, project_session([other, sgb]), "t").project()
    assert project.ontology_iri == sgb
    with pytest.raises(DspError):
        Dsp(SETTINGS, project_session([other]), "t").project()
