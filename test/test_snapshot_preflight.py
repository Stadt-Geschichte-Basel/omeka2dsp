"""Tests for the snapshot reader and the payload preflight."""

import json

from preflight import preflight
from snapshot_source import load_snapshot, media_by_item, select

ONTOLOGY = {
    "@graph": [
        {
            "@id": "SGB:Parent",
            "@type": "owl:Class",
            "rdfs:subClassOf": [
                {"owl:onProperty": {"@id": "SGB:hasTitle"}},
                {"owl:onProperty": {"@id": "SGB:hasLanguageList"}},
            ],
        },
        {
            "@id": "SGB:hasTitle",
            "@type": "owl:ObjectProperty",
            "knora-api:objectType": {"@id": "knora-api:TextValue"},
        },
        {
            "@id": "SGB:hasLanguageList",
            "@type": "owl:ObjectProperty",
            "knora-api:objectType": {"@id": "knora-api:ListValue"},
        },
    ]
}


def item(identifier, o_id=1):
    return {"o:id": o_id, "dcterms:identifier": [{"@value": identifier}]}


def test_load_snapshot_prefers_transformed(tmp_path):
    (tmp_path / "items_raw.json").write_text(json.dumps([item("raw")]))
    (tmp_path / "items_transformed.json").write_text(json.dumps([item("clean")]))
    (tmp_path / "media_raw.json").write_text(json.dumps([]))

    items, media = load_snapshot(tmp_path)

    assert items == [item("clean")]
    assert media == []


def test_media_by_item_and_select():
    media = [{"o:id": 10, "o:item": {"o:id": 1}}, {"o:id": 11, "o:item": {"o:id": 2}}]
    assert media_by_item(media) == {1: [media[0]], 2: [media[1]]}
    items = [item("abb1", 1), item("abb2", 2)]
    assert select(items, {"abb2"}) == [items[1]]


def test_preflight_accepts_valid_payload():
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": {"@type": "knora-api:TextValue"},
    }
    assert preflight(payload, {}, ONTOLOGY, "SGB:") == []


def test_preflight_reports_wrong_type_unknown_property_and_unresolved_list():
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": [{"@type": "knora-api:UriValue"}],
        "SGB:hasCreator": {"@type": "knora-api:TextValue"},
    }
    source = {"dcterms:language": [{"@value": "de"}]}

    problems = preflight(payload, source, ONTOLOGY, "SGB:")

    assert len(problems) == 3
    assert any("UriValue" in p for p in problems)
    assert any("hasCreator is not allowed" in p for p in problems)
    assert any("hasLanguageList: no list node" in p for p in problems)


def test_preflight_unknown_class():
    assert preflight({"@type": "SGB:Nope"}, {}, ONTOLOGY, "SGB:") == [
        "unknown class SGB:Nope"
    ]


def test_preflight_reports_missing_object_type_and_missing_value_type():
    ontology = {
        "@graph": [
            {
                "@id": "SGB:Parent",
                "@type": "owl:Class",
                "rdfs:subClassOf": [
                    {"owl:onProperty": {"@id": "SGB:hasTitle"}},
                    {"owl:onProperty": {"@id": "SGB:hasNote"}},
                ],
            },
            ONTOLOGY["@graph"][1],
            {"@id": "SGB:hasNote", "@type": "owl:ObjectProperty"},
        ]
    }
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": {"knora-api:valueAsString": "x"},
        "SGB:hasNote": {"knora-api:valueAsString": "y"},
    }
    assert preflight(payload, {}, ontology, "SGB:") == [
        "SGB:hasTitle: value has no @type",
        "SGB:hasNote: no knora-api:objectType in the ontology",
    ]
