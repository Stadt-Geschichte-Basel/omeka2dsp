from omeka2dsp.preflight import preflight
from omeka2dsp.values import OmekaRecord

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
EMPTY = OmekaRecord()


def test_preflight_accepts_valid_payload():
    payload = {"@type": "SGB:Parent", "SGB:hasTitle": {"@type": "knora-api:TextValue"}}
    assert preflight(payload, EMPTY, ONTOLOGY, "SGB:") == []


def test_preflight_reports_wrong_type_unknown_property_and_unresolved_list():
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": [{"@type": "knora-api:UriValue"}],
        "SGB:hasCreator": {"@type": "knora-api:TextValue"},
    }
    source = OmekaRecord.parse({"dcterms:language": [{"@value": "de"}]})
    problems = preflight(payload, source, ONTOLOGY, "SGB:")
    assert len(problems) == 3
    assert any("UriValue" in p for p in problems)
    assert any("hasCreator is not allowed" in p for p in problems)
    assert any("hasLanguageList: no list node" in p for p in problems)


def test_preflight_unknown_class():
    assert preflight({"@type": "SGB:Nope"}, EMPTY, ONTOLOGY, "SGB:") == [
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
    assert preflight(payload, EMPTY, ontology, "SGB:") == [
        "SGB:hasTitle: value has no @type",
        "SGB:hasNote: no knora-api:objectType in the ontology",
    ]
