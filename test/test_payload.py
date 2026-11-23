import json
from pathlib import Path

from omeka2dsp import payload
from omeka2dsp.fields import Project
from omeka2dsp.plan import Change
from omeka2dsp.values import OmekaRecord

PROJECT = Project(iri="p", shortcode="0001", ontology_name="SGB", ontology_iri="o")
RESOURCE = {"@id": "r", "@type": "SGB:Image"}
MODEL = json.loads(
    (Path(__file__).parent.parent / "data" / "data_model_dasch.json").read_text()
)


def test_text_payload_has_text_file_value():
    body = payload.create(PROJECT, "Text", OmekaRecord(), [], "parent", "x.csv")
    assert body["knora-api:hasTextFileValue"] == {
        "@type": "knora-api:TextFileValue",
        "knora-api:fileValueHasFilename": "x.csv",
    }
    assert body["SGB:linkToParentObjectValue"]["@type"] == "knora-api:LinkValue"


def test_media_payload_has_no_is_part_of():
    """The ontology allows isPartOf only on Parent."""
    record = OmekaRecord.parse({"dcterms:isPartOf": [{"@value": "Band 4"}]})
    assert "SGB:isPartOf" in payload.create(PROJECT, "Parent", record, [])
    assert "SGB:isPartOf" not in payload.create(PROJECT, "Image", record, [])


def test_change_bodies():
    def value(action, **kw):
        change = Change(
            field="hasTitle", action=action, value_type="knora-api:TextValue", **kw
        )
        return payload.change(PROJECT, RESOURCE, change)["SGB:hasTitle"]

    assert value("create", value="T") == {
        "@type": "knora-api:TextValue",
        "knora-api:valueAsString": "T",
    }
    assert value("update", value="T", value_id="v")["@id"] == "v"
    assert value("delete", value="T", value_id="v") == {
        "@id": "v",
        "@type": "knora-api:TextValue",
    }


def test_text_class_copies_document_properties():
    project = PROJECT.model_copy(
        update={"ontology_iri": "http://x/ontology/4001/SGB/v2"}
    )
    body = payload.text_class(MODEL, project, {"@value": "t"})
    [cls] = body["@graph"]
    assert cls["@id"] == "SGB:Text"
    assert cls["rdfs:subClassOf"][0] == {"@id": "knora-api:TextRepresentation"}
    restrictions = {r["owl:onProperty"]["@id"]: r for r in cls["rdfs:subClassOf"][1:]}
    assert "SGB:linkToParentObject" in restrictions
    assert restrictions["SGB:hasTitle"]["owl:cardinality"] == 1


def _keys(node):
    """Yield every dict key in a JSON tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def test_data_model_has_no_subject_list():
    """Subjects are discontinued."""
    assert "hasSubjectList" not in json.dumps(MODEL)
    assert "subject" not in {str(k).lower() for k in _keys(MODEL)}


def test_create_payload_ignores_dcterms_subject():
    record = OmekaRecord.parse({"dcterms:subject": [{"@value": "Stadt"}]})
    body = payload.create(PROJECT, "Parent", record, [])
    assert not [key for key in body if "Subject" in key]


def test_target_fixtures_have_no_subject_list():
    data = Path(__file__).parent.parent / "data"
    for path in [*data.glob("example_payload_*"), *data.glob("example_api_get_*")]:
        assert "hasSubjectList" not in path.read_text(), path.name
