from omeka2dsp.preflight import index_ontology, preflight
from omeka2dsp.values import OmekaRecord

ONTOLOGY = {
    "@graph": [
        {
            "@id": "SGB:Parent",
            "@type": "owl:Class",
            "rdfs:subClassOf": [
                {"owl:onProperty": {"@id": "SGB:hasTitle"}},
                {"owl:onProperty": {"@id": "SGB:hasLanguageList"}},
                {
                    "owl:onProperty": {"@id": "SGB:isPartOf"},
                    "owl:maxCardinality": {"@value": 1},
                },
            ],
        },
        {
            "@id": "SGB:Image",
            "@type": "owl:Class",
            "rdfs:subClassOf": [{"owl:onProperty": {"@id": "SGB:hasTitle"}}],
        },
        {
            "@id": "SGB:isPartOf",
            "@type": "owl:ObjectProperty",
            "knora-api:objectType": {"@id": "knora-api:TextValue"},
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
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": {
            "@type": "knora-api:TextValue",
            "knora-api:valueAsString": "x",
        },
    }
    assert preflight(payload, EMPTY, ONTOLOGY, "SGB:") == []


def test_preflight_reports_wrong_type_unknown_property_and_unresolved_list():
    payload = {
        "@type": "SGB:Parent",
        "SGB:hasTitle": [{"@type": "knora-api:UriValue"}],
        "SGB:hasCreator": {
            "@type": "knora-api:TextValue",
            "knora-api:valueAsString": "x",
        },
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
            ONTOLOGY["@graph"][3],
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


def text(value: str = "x") -> dict:
    return {"@type": "knora-api:TextValue", "knora-api:valueAsString": value}


def test_index_ontology_reads_int_and_dict_cardinalities():
    ontology = {
        "@graph": [
            {
                "@id": "SGB:Parent",
                "@type": "owl:Class",
                "rdfs:subClassOf": [
                    {"owl:onProperty": {"@id": "SGB:a"}, "owl:maxCardinality": 2},
                    {
                        "owl:onProperty": {"@id": "SGB:b"},
                        "owl:cardinality": {"@value": 1},
                    },
                    {"owl:onProperty": {"@id": "SGB:c"}},
                ],
            }
        ]
    }
    limits = index_ontology(ontology)[2]
    assert limits == {("SGB:Parent", "SGB:a"): 2, ("SGB:Parent", "SGB:b"): 1}


def test_preflight_reports_too_many_values():
    payload = {"@type": "SGB:Parent", "SGB:isPartOf": [text("a"), text("b")]}
    assert preflight(payload, EMPTY, ONTOLOGY, "SGB:") == [
        "SGB:isPartOf: 2 values, at most 1 allowed"
    ]


def test_preflight_reports_empty_value():
    payload = {"@type": "SGB:Parent", "SGB:hasTitle": text("")}
    assert preflight(payload, EMPTY, ONTOLOGY, "SGB:") == ["SGB:hasTitle: empty value"]


def test_preflight_reports_invalid_uri():
    record = OmekaRecord.parse(
        {"dcterms:isPartOf": [{"@id": "Hans Holbein d. j.", "o:label": "Holbein"}]}
    )
    payload = {"@type": "SGB:Parent", "SGB:hasTitle": text()}
    assert preflight(payload, record, ONTOLOGY, "SGB:") == [
        "SGB:isPartOf: invalid URI 'Hans Holbein d. j.'"
    ]


def test_preflight_reports_file_that_does_not_fit_class():
    record = OmekaRecord(original_url="https://x.test/files/original/m77123.jpx")
    payload = {"@type": "SGB:Image", "SGB:hasTitle": text()}
    assert preflight(payload, record, ONTOLOGY, "SGB:") == [
        "file 'm77123.jpx' does not fit class Image"
    ]
    ok = OmekaRecord(original_url="https://x.test/files/original/a.JPG")
    assert preflight(payload, ok, ONTOLOGY, "SGB:") == []
