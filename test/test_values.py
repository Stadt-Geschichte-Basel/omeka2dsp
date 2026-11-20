from omeka2dsp.fields import FIELDS
from omeka2dsp.values import (
    OmekaRecord,
    OmekaValue,
    entry_key,
    first_literal,
    labels,
    text_entries,
    wanted,
)

DOI = OmekaValue.model_validate(
    {
        "@id": "https://doi.org/10.21255/sgb-04-283636",
        "o:label": "Aufbrüche, Krisen & Transformationen",
    }
)
FIELD = {field.prop: field for field in FIELDS}


def test_uri_value_becomes_standoff_link():
    [entry] = text_entries([DOI])
    assert "knora-api:valueAsString" not in entry
    assert entry["knora-api:textValueHasMapping"]["@id"].endswith("StandardMapping")
    assert entry_key(entry) == (
        "xml",
        "Aufbrüche, Krisen & Transformationen",
        ("https://doi.org/10.21255/sgb-04-283636",),
    )


def test_literal_value_stays_unformatted():
    [entry] = text_entries([OmekaValue.model_validate({"@value": " Burghartz; S "})])
    assert entry == {
        "@type": "knora-api:TextValue",
        "knora-api:valueAsString": "Burghartz; S",
    }


def test_text_takes_the_first_literal():
    values = [DOI, OmekaValue.model_validate({"@value": "1538"})]
    assert first_literal(values) == "1538"
    assert labels(values) == ["Aufbrüche, Krisen & Transformationen", "1538"]


def test_abstract_keeps_the_semicolon_entity():
    record = OmekaRecord.parse({"dcterms:abstract": [{"@value": "a; b"}]})
    assert wanted(FIELD["hasAbstract"], record, []).values == ("a&#59 b",)
    linked = OmekaRecord.parse({"dcterms:abstract": [{"@id": "u;1", "o:label": "x"}]})
    assert wanted(FIELD["hasAbstract"], linked, []).values == (
        "<a href='u&#591'>x</a>",
    )


def test_record_flags_and_identifier():
    record = OmekaRecord.parse(
        {
            "o:id": 3,
            "o:item": {"o:id": 1},
            "o:is_public": False,
            "dcterms:identifier": [{"property_id": 10, "@value": "m1"}],
        }
    )
    assert (record.id, record.item_id, record.identifier) == (3, 1, "m1")
    assert record.private


def test_privacy_flags():
    def private(raw):
        return OmekaRecord.parse(raw).private

    assert not private({})
    assert not private({"o:is_public": True})
    assert private({"o:is_public": False})
    assert private({"o:private": True})
    assert not private({"o:private": False, "o:is_public": True})


def test_unresolved_list_labels_are_reported():
    record = OmekaRecord.parse({"dcterms:type": [{"@id": "u", "o:label": "Image"}]})
    assert wanted(FIELD["hasTypeList"], record, []) == ((), ("Image",))
