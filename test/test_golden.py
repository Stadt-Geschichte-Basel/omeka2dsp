"""Golden tests: request bodies for the example Omeka records.

The expected bodies are in test/golden/. Set GOLDEN_UPDATE=1 to write them again.
"""

import ast
import json
import os
from pathlib import Path

import pytest

import data_2_dasch as d
from omeka2dsp import payload
from omeka2dsp.fields import Project
from omeka2dsp.values import OmekaRecord

ROOT = Path(__file__).parent.parent
GOLDEN = Path(__file__).parent / "golden"
PARENT_IRI = "http://rdfh.ch/4001/parent"
PROJECT_IRI = "http://rdfh.ch/projects/4001"
PROJECT = Project(
    iri=PROJECT_IRI,
    shortcode="TEST",
    ontology_name="SGB",
    ontology_iri="https://api.test.com/ontology/TEST/SGB/v2",
)


def node(list_iri, label):
    return {"@id": f"{list_iri}/{label}", "rdfs:label": label}


LISTS = [
    *json.loads((ROOT / "data" / "example_api_get_listvalues.json").read_text()),
    {
        "rdfs:label": "Stadt.Geschichte.Basel Epoche",
        "knora-api:hasSubListNode": [node("http://rdfh.ch/lists/era", "Frühe Neuzeit")],
    },
    {
        "rdfs:label": "ISO 639-1",
        "knora-api:hasSubListNode": [node("http://rdfh.ch/lists/lang", "de")],
    },
    {
        "rdfs:label": "Licenses",
        "knora-api:hasSubListNode": [
            node(
                "http://rdfh.ch/lists/license",
                "https://creativecommons.org/publicdomain/mark/1.0/",
            )
        ],
    },
]


def omeka(name):
    return ast.literal_eval((ROOT / "data" / f"example_omeka_{name}").read_text())


def dsp(name):
    return json.loads((ROOT / "data" / f"example_api_get_{name}.json").read_text())


ITEM = omeka("object")
# The example media has no abstract and no isPartOf. Add both to record them.
MEDIA = {
    **omeka("media"),
    "dcterms:abstract": [{"property_id": 19, "@value": "Karte; Basel"}],
    "dcterms:isPartOf": [{"property_id": 33, "@value": "Band 4"}],
}


def payloads():
    item, media = OmekaRecord.parse(ITEM), OmekaRecord.parse(MEDIA)
    return {
        "parent": payload.create(PROJECT, "Parent", item, LISTS),
        **{
            cls: payload.create(PROJECT, cls, media, LISTS, PARENT_IRI, filename)
            for cls, filename in [
                ("Image", "x.jp2"),
                ("Text", "x.csv"),
                ("Document", "x.pdf"),
                ("ResourceWithoutMedia", None),
            ]
        },
    }


def change_requests(monkeypatch):
    """The value requests that sync sends for the example DSP resources."""
    sent = []

    class Response:
        status_code, text = 200, ""

    def capture(method):
        def send(url, json, **kwargs):
            sent.append({"method": method, "url": url, "body": json})
            return Response()

        return send

    monkeypatch.setattr(d.requests, "post", capture("POST"))
    monkeypatch.setattr(d.requests, "put", capture("PUT"))
    for resource, source in [(dsp("OBJEKT"), ITEM), (dsp("MEDIA"), MEDIA)]:
        for change in d.check_values(resource, source, LISTS):
            d.update_value(
                "token",
                resource,
                change["value"],
                change["field"],
                change["prop_type"],
                change["type"],
            )
    return sorted(sent, key=lambda r: json.dumps(r, sort_keys=True))


def check(name, actual):
    path = GOLDEN / f"{name}.json"
    text = json.dumps(actual, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("GOLDEN_UPDATE"):
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
    # Compare parsed JSON: prettier formats the files in the pre-commit hook.
    assert json.loads(text) == json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name", ["parent", "Image", "Text", "Document", "ResourceWithoutMedia"]
)
def test_create_payload(name):
    check(f"create_{name}", payloads()[name])


def test_change_requests(monkeypatch):
    check("changes", change_requests(monkeypatch))
