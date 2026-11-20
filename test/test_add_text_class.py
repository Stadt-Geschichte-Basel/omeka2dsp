import json
from pathlib import Path

from add_text_class import class_request

MODEL = json.loads(
    (Path(__file__).parent.parent / "data" / "data_model_dasch.json").read_text()
)


def test_text_class_copies_document_properties():
    body = class_request(MODEL, "http://x/ontology/4001/SGB/v2", {"@value": "t"})
    [cls] = body["@graph"]
    assert cls["@id"] == "SGB:Text"
    assert cls["rdfs:subClassOf"][0] == {"@id": "knora-api:TextRepresentation"}
    props = [r["owl:onProperty"]["@id"] for r in cls["rdfs:subClassOf"][1:]]
    assert "SGB:hasTitle" in props and "SGB:linkToParentObject" in props
    title = next(
        r
        for r in cls["rdfs:subClassOf"][1:]
        if r["owl:onProperty"]["@id"] == "SGB:hasTitle"
    )
    assert title["owl:cardinality"] == 1
