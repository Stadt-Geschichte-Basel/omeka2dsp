"""Safety rules of the sync flow (SPECS.md section 10)."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest
import requests
from omeka_s_client import OmekaClient
from omeka_s_client.testing import FakeOmeka

from fakes import SETTINGS
from omeka2dsp import media as media_rules
from omeka2dsp import sync
from omeka2dsp.dsp import Dsp, DspError
from omeka2dsp.fields import Project
from omeka2dsp.sync import Context, Options, Selection
from omeka2dsp.values import OmekaRecord

PROJECT = Project(iri="p", shortcode="TEST", ontology_name="SGB", ontology_iri="o")
CSV = OmekaRecord.parse(
    {
        "o:id": 5,
        "dcterms:identifier": [{"@value": "m1"}],
        "dcterms:format": [{"@value": "text/csv"}],
        "o:original_url": "https://omeka.test.com/files/m1.csv",
    }
)
ITEM = OmekaRecord.parse({"o:id": 1, "dcterms:identifier": [{"@value": "abb1"}]})


@dataclass(frozen=True)
class FakeDsp(Dsp):
    """Records the calls. found maps (class, identifier) to an IRI."""

    calls: list[str] = field(default_factory=list)
    found: dict[tuple[str, str], str] = field(default_factory=dict)
    fail: frozenset[str] = frozenset()
    file: bytes = b"a,b"
    resources: dict[str, Any] = field(default_factory=dict)

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise DspError(f"{name} failed")

    def find(self, project, resource_class, identifier):
        return self.found.get((resource_class, identifier))

    def resource(self, iri):
        return self.resources.get(
            iri, {"@id": iri, "@type": "SGB:ResourceWithoutMedia"}
        )

    def create(self, body):
        self._call("create")
        return "new-iri"

    def change(self, action, body):
        self._call(action)

    def restrict(self, body):
        self._call("restrict")

    def erase(self, body):
        self._call("erase")

    def ingest(self, filename, content):
        self._call("ingest")
        return "internal.csv"


def context(dsp: FakeDsp, **options) -> Context:
    """A context whose Omeka client serves dsp.file and logs a "download" call."""

    class Files(FakeOmeka):
        def __call__(self, request):
            dsp.calls.append("download")
            return super().__call__(request)

    files = Files(files={"/files/m1.csv": dsp.file})
    omeka = OmekaClient(SETTINGS.omeka_api_url, transport=files, sleep=lambda _: None)
    return Context(dsp, PROJECT, [], {}, omeka, Options(**options))


@pytest.fixture
def preflight_ok(monkeypatch):
    monkeypatch.setattr(sync, "preflight", lambda *a: [])


def in_wrong_class(**kw) -> FakeDsp:
    """m1 exists as ResourceWithoutMedia, but the source maps to Text."""
    return FakeDsp(
        SETTINGS,
        requests.Session(),
        found={("SGB:ResourceWithoutMedia", "m1"): "old"},
        **kw,
    )


def test_recreate_keeps_old_record_when_preflight_fails(monkeypatch):
    """Safety rule 3."""
    monkeypatch.setattr(sync, "preflight", lambda *a: ["bad"])
    dsp = in_wrong_class()
    sync.sync_media(context(dsp, recreate=frozenset({"m1"})), CSV, "parent")
    assert dsp.calls == []


def test_recreate_keeps_old_record_when_ingest_fails(preflight_ok):
    """Safety rule 3."""
    dsp = in_wrong_class(fail=frozenset({"ingest"}))
    sync.sync_media(context(dsp, recreate=frozenset({"m1"})), CSV, "parent")
    assert dsp.calls == ["download", "ingest"]


def test_recreate_keeps_old_record_when_download_fails(preflight_ok):
    """A missing Omeka file stops the media before the ingest and the erase."""
    dsp = in_wrong_class()
    ctx = context(dsp, recreate=frozenset({"m1"}))
    missing = CSV.model_copy(
        update={"original_url": "https://omeka.test.com/files/gone.csv"}
    )
    sync.sync_media(ctx, missing, "parent")
    assert dsp.calls == ["download"]


def test_recreate_erases_only_after_ingest(preflight_ok):
    dsp = in_wrong_class()
    sync.sync_media(context(dsp, recreate=frozenset({"m1"})), CSV, "parent")
    assert dsp.calls == ["download", "ingest", "erase", "create"]


def test_wrong_class_without_recreate_syncs_values_only(preflight_ok):
    dsp = in_wrong_class()
    sync.sync_media(context(dsp), CSV, "parent")
    assert "erase" not in dsp.calls and "create" not in dsp.calls


def test_item_without_parent_skips_its_media(preflight_ok):
    """Safety rule 4."""
    dsp = FakeDsp(SETTINGS, requests.Session(), fail=frozenset({"create"}))
    seen = []
    sync.sync_item(context(dsp), ITEM, lambda item: seen.append(item) or [CSV])
    assert dsp.calls == ["create"] and seen == []


def test_placeholder_file_is_not_ingested(monkeypatch, preflight_ok):
    """Safety rule 8: a wrong o:sha256 must not let the placeholder through."""
    content = b"placeholder bytes"
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(media_rules, "PLACEHOLDER_SHA256", frozenset({digest}))
    dsp = FakeDsp(SETTINGS, requests.Session(), file=content)
    sync.sync_media(context(dsp), CSV, "parent")
    assert dsp.calls == ["download"]


def test_private_media_restricts_existing_file(preflight_ok):
    """Safety rule 7: a private media that DSP holds as Image gets its file hidden."""
    image = {
        "@id": "img",
        "@type": "SGB:Image",
        "knora-api:hasStillImageFileValue": {
            "@id": "v",
            "@type": "knora-api:StillImageFileValue",
            "knora-api:hasPermissions": "V knora-admin:UnknownUser",
        },
    }
    dsp = FakeDsp(
        SETTINGS,
        requests.Session(),
        found={("SGB:Image", "m1"): "img"},
        resources={"img": image},
    )
    private = CSV.model_copy(update={"private": True})
    sync.sync_media(context(dsp), private, "parent")
    assert "restrict" in dsp.calls
    assert "download" not in dsp.calls and "ingest" not in dsp.calls


def test_private_file_is_restricted_before_metadata_changes(preflight_ok):
    """A timeout in a metadata change must not leave the file public."""

    @dataclass(frozen=True)
    class TimeoutDsp(FakeDsp):
        def change(self, action, body):
            self.calls.append(action)
            raise requests.Timeout("metadata change timed out")

    image = {
        "@id": "img",
        "@type": "SGB:Image",
        "SGB:hasTitle": {
            "@id": "t",
            "@type": "knora-api:TextValue",
            "knora-api:valueAsString": "old",
        },
        "knora-api:hasStillImageFileValue": {
            "@id": "v",
            "@type": "knora-api:StillImageFileValue",
            "knora-api:hasPermissions": "V knora-admin:UnknownUser",
        },
    }
    dsp = TimeoutDsp(
        SETTINGS,
        requests.Session(),
        found={("SGB:Image", "m1"): "img"},
        resources={"img": image},
    )
    private = CSV.model_copy(update={"private": True})
    with pytest.raises(requests.Timeout):
        sync.sync_media(context(dsp), private, "parent")
    assert dsp.calls[0] == "restrict"


def test_private_media_is_created_without_file(preflight_ok):
    """Safety rule 7."""
    dsp = FakeDsp(SETTINGS, requests.Session())
    sync.sync_media(context(dsp), CSV.model_copy(update={"private": True}), "parent")
    assert dsp.calls == ["create"]


def test_dry_run_writes_nothing(preflight_ok):
    dsp = FakeDsp(SETTINGS, requests.Session(), found={("SGB:Parent", "abb1"): "iri"})
    resource = {"@id": "iri", "@type": "SGB:Parent", "SGB:hasSubjectList": {"@id": "s"}}
    dsp.resources["iri"] = resource
    sync.sync_item(context(dsp, dry_run=True), ITEM, lambda item: [CSV])
    assert dsp.calls == []


def test_empty_selection_selects_no_item(tmp_path):
    (tmp_path / "items.json").write_text(
        json.dumps([{"o:id": 1, "dcterms:identifier": [{"@value": "abb1"}]}])
    )
    (tmp_path / "media.json").write_text("[]")
    omeka = OmekaClient(SETTINGS.omeka_api_url, transport=FakeOmeka())
    found, _ = sync.load(SETTINGS, omeka, Selection(tmp_path, frozenset()))
    assert found == []
    every, _ = sync.load(SETTINGS, omeka, Selection(tmp_path))
    assert len(every) == 1


def test_load_selects_from_a_snapshot(tmp_path):
    items = [
        {"o:id": n, "dcterms:identifier": [{"@value": f"abb{n}"}]} for n in (1, 2, 3)
    ]
    media = [{"o:id": 9, "o:item": {"o:id": 2}}]
    (tmp_path / "items.json").write_text(json.dumps(items))
    (tmp_path / "media.json").write_text(json.dumps(media))
    selection = Selection(tmp_path, frozenset({"abb2", "abb3"}), sample=1)
    omeka = OmekaClient(SETTINGS.omeka_api_url, transport=FakeOmeka())
    found, media_of = sync.load(SETTINGS, omeka, selection)
    assert len(found) == 1 and found[0].identifier in {"abb2", "abb3"}
    assert [m.id for m in media_of(OmekaRecord.parse(items[1]))] == [9]


class RunDsp(FakeDsp):
    def project(self):
        return PROJECT

    def lists(self, project):
        return []

    def ontology(self, project):
        return {}


def run_snapshot(monkeypatch, tmp_path, identifiers):
    """Run a snapshot of items with these identifiers. Return (DSP, error count)."""
    items = [
        {"o:id": n, "dcterms:identifier": [{"@value": i}]}
        for n, i in enumerate(identifiers, start=1)
    ]
    (tmp_path / "items.json").write_text(json.dumps(items))
    (tmp_path / "media.json").write_text("[]")
    dsp = RunDsp(SETTINGS, requests.Session())
    monkeypatch.setattr(sync, "Dsp", type("Login", (), {"login": lambda *a: dsp}))
    omeka = OmekaClient(SETTINGS.omeka_api_url, transport=FakeOmeka())
    errors = sync.run(
        SETTINGS, Selection(tmp_path), Options(), requests.Session(), omeka
    )
    return dsp, errors


def test_duplicate_identifiers_write_nothing(monkeypatch, tmp_path, preflight_ok):
    dsp, errors = run_snapshot(monkeypatch, tmp_path, ["abb1", "abb1"])
    assert dsp.calls == [] and errors > 0


def test_duplicates_do_not_stop_other_items(monkeypatch, tmp_path, preflight_ok):
    dsp, errors = run_snapshot(monkeypatch, tmp_path, ["abb1", "abb1", "abb2"])
    assert dsp.calls == ["create"] and errors == 1


def test_clean_run_returns_no_errors(monkeypatch, tmp_path, preflight_ok):
    dsp, errors = run_snapshot(monkeypatch, tmp_path, ["abb1", "abb2"])
    assert dsp.calls == ["create", "create"] and errors == 0


def test_media_identifier_is_synced_once(preflight_ok):
    dsp = FakeDsp(SETTINGS, requests.Session())
    ctx = context(dsp)
    sync.sync_media(ctx, CSV, "parent")
    sync.sync_media(ctx, CSV, "parent")
    assert dsp.calls.count("create") == 1
