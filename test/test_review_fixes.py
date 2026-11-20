"""Guards from the PR #20 review: no deletions or erasures on a failed step."""

import pytest

import data_2_dasch as d
from data_2_dasch import PREFIX

LISTS = [
    {
        "rdfs:label": "ISO 639-1",
        "knora-api:hasSubListNode": [{"@id": "iri-de", "rdfs:label": "de"}],
    }
]


def test_unresolved_list_label_keeps_dsp_value():
    assert (
        d.list_value_change("hasLanguageList", "iri-de", "xx", "language", LISTS)
        is None
    )


def test_absent_source_value_still_deletes():
    change = d.list_value_change("hasLanguageList", "iri-de", "", "language", LISTS)
    assert change["type"] == "delete"


class Response:
    def __init__(self, status, data=None):
        self.status_code, self._data, self.text = status, data, ""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(self.status_code)


def test_failed_list_request_aborts(monkeypatch):
    monkeypatch.setattr(d.requests, "get", lambda *a, **k: Response(500))
    with pytest.raises(RuntimeError):
        d.get_lists("project")


MEDIA = {
    "dcterms:identifier": [{"property_id": 10, "@value": "m1"}],
    "dcterms:format": [{"property_id": 9, "@value": "text/csv"}],
    "o:original_url": "https://omeka/files/m1.csv",
}


@pytest.fixture
def recreate_env(monkeypatch):
    """m1 exists as ResourceWithoutMedia but now maps to Text."""
    calls = []
    monkeypatch.setattr(
        d, "find_media", lambda *a: ("old-iri", f"{PREFIX}ResourceWithoutMedia")
    )
    monkeypatch.setattr(d, "get_full_resource", lambda *a: {"@id": "old-iri"})
    monkeypatch.setattr(d, "erase_resource", lambda *a: calls.append("erase") or True)
    monkeypatch.setattr(d, "create_resource", lambda *a: calls.append("create") or True)
    monkeypatch.setattr(d, "construct_payload", lambda *a: {"@type": f"{PREFIX}Text"})
    return calls


def run(**kw):
    d.sync_media(
        "t", MEDIA, "parent", "p", [], {}, dry_run=False, recreate={"m1"}, **kw
    )


def test_recreate_keeps_old_record_when_preflight_fails(monkeypatch, recreate_env):
    monkeypatch.setattr(d, "check_payload", lambda *a: False)
    run()
    assert recreate_env == []


def test_recreate_keeps_old_record_when_ingest_fails(monkeypatch, recreate_env):
    monkeypatch.setattr(d, "check_payload", lambda *a: True)
    monkeypatch.setattr(d, "upload_file_from_url", lambda *a: None)
    run()
    assert recreate_env == []


def test_recreate_erases_only_after_ingest(monkeypatch, recreate_env):
    monkeypatch.setattr(d, "check_payload", lambda *a: True)
    monkeypatch.setattr(
        d, "upload_file_from_url", lambda *a: recreate_env.append("ingest") or "f.csv"
    )
    run()
    assert recreate_env == ["ingest", "erase", "create"]


def test_public_placeholder_hides_existing_file(monkeypatch):
    """A placeholder that DSP holds as an Image must get restricted permissions."""
    seen = {}
    placeholder = {
        **MEDIA,
        "o:sha256": next(iter(d.PLACEHOLDER_SHA256)),
        "o:is_public": True,
    }
    monkeypatch.setattr(d, "find_media", lambda *a: ("iri", f"{PREFIX}Image"))
    monkeypatch.setattr(d, "sync_existing", lambda *a: {"@id": "iri"})
    monkeypatch.setattr(
        d, "sync_file_permissions", lambda t, r, hide, *a: seen.update(hide=hide)
    )
    d.sync_media("t", placeholder, "parent", "p", [], {}, dry_run=True)
    assert seen == {"hide": True}
